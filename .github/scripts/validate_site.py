#!/usr/bin/env python3
"""Validate only the generated site/ tree. No access to private source is required."""
import argparse
import json
import pathlib
import re
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
BLOCKED_DIRS = {".git", ".github", "content", "src", "scripts", "tests", "docs", "node_modules", "research", "credentials", "private"}
BLOCKED_NAMES = {".env", ".gitignore", ".npmrc", "package.json", "package-lock.json",
                 "publication-review.json", "boss-commercial-review-casefiles.json",
                 "commercial-launch-register.json"}
BLOCKED_EXT = {".md", ".ps1", ".sh", ".yaml", ".yml", ".pem", ".key", ".log", ".map", ".p12", ".pfx"}
TEXT_EXT = {".html", ".xml", ".txt", ".json", ".js", ".mjs", ".css", ".svg"}
SECRET_PATTERNS = [
    ("private-key", re.compile(r"-----BEGIN (?:OPENSSH |RSA |EC |DSA )?PRIVATE KEY-----")),
    ("github-token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{30,}\b")),
    ("aws-access-key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
]
NOINDEX = re.compile(r'<meta\s+name="robots"\s+content="[^"]*\bnoindex\b[^"]*"', re.I)
AD_TAG = re.compile(r"adsbygoogle|pagead2\.googlesyndication\.com|google_ad_client", re.I)

def audit(site: pathlib.Path):
    errors = []
    count = 0
    if not site.is_dir():
        return ["No site/ folder exists yet. This repository is deliberately not publishing anything."], count
    if not (site / "index.html").is_file():
        errors.append("Missing homepage: site/index.html")
    if not (site / "catalog.json").is_file():
        errors.append("Missing public dataset: site/catalog.json")
    if not (site / ".nojekyll").is_file() or (site / ".nojekyll").stat().st_size != 0:
        errors.append("Missing or nonempty site/.nojekyll marker")
    sitemap = site / "sitemap.xml"
    if not sitemap.is_file() or re.search(r"<loc\s*>", sitemap.read_text(encoding="utf-8"), re.I):
        errors.append("Beta sitemap must exist and contain zero URL entries")
    robots = site / "robots.txt"
    if not robots.is_file() or re.search(r"^\s*Disallow:\s*/\s*$", robots.read_text(encoding="utf-8"), re.M):
        errors.append("Do not block crawling in robots.txt: crawlers must be able to see noindex")

    for path in site.rglob("*"):
        relative = path.relative_to(site).as_posix()
        if path.is_symlink():
            errors.append(f"Symlink forbidden in public site: {relative}")
            continue
        if path.is_dir():
            if any(part in BLOCKED_DIRS for part in path.relative_to(site).parts):
                errors.append(f"Private directory in site: {relative}")
            continue
        if not path.is_file():
            errors.append(f"Unexpected filesystem object: {relative}")
            continue
        count += 1
        if relative == ".nojekyll":
            continue
        if any(part in BLOCKED_DIRS for part in path.relative_to(site).parts[:-1]):
            continue
        if (path.name in BLOCKED_NAMES or path.name.startswith(".") or
                path.suffix.lower() in BLOCKED_EXT):
            errors.append(f"Source/development file in site: {relative}")
            continue
        if path.suffix.lower() not in TEXT_EXT:
            continue
        content = path.read_text(encoding="utf-8")
        for kind, regex in SECRET_PATTERNS:
            if regex.search(content):
                errors.append(f"{kind} pattern detected in: {relative}")
        if path.suffix.lower() == ".html":
            if not NOINDEX.search(content):
                errors.append(f"Indexable beta page: {relative}")
            if AD_TAG.search(content):
                errors.append(f"Advertising scripts not allowed before approval: {relative}")
        if path.suffix.lower() == ".json":
            try:
                data = json.loads(content)
            except ValueError:
                errors.append(f"Invalid JSON: {relative}")
                continue
            if re.fullmatch(r"catalog(?:[-.][a-z0-9-]+)*\.json", path.name):
                if isinstance(data, dict):
                    for champ in data.get("champions", []):
                        ref = champ.get("referenceFacts") or {}
                        if (ref.get("status") not in (None, "source-link-only")
                                or any(key in ref for key in ("abilities", "protections", "battlecast", "statcast"))):
                            errors.append(f"Unapproved source compilation: {relative}/{champ.get('id')}")
                        if (champ.get("relicIds") or
                                (champ.get("loadout") or {}).get("battlecastId") or
                                (champ.get("loadout") or {}).get("statcastId")):
                            errors.append(f"Unreviewed relic pairing: {relative}/{champ.get('id')}")
    return errors, count


def self_test():
    with tempfile.TemporaryDirectory(prefix="summoner-public-guard-") as temp:
        site = pathlib.Path(temp) / "site"
        site.mkdir()
        (site / "index.html").write_text('<meta name="robots" content="noindex,follow">', encoding="utf-8")
        (site / "catalog.json").write_text(json.dumps({"champions": []}), encoding="utf-8")
        (site / "sitemap.xml").write_text("<urlset></urlset>", encoding="utf-8")
        (site / "robots.txt").write_text("User-agent: *\nAllow: /\n", encoding="utf-8")
        (site / ".nojekyll").touch()
        assert not audit(site)[0], audit(site)
        (site / "index.html").write_text('<meta name="robots" content="index,follow">', encoding="utf-8")
        assert any("Indexable" in e for e in audit(site)[0])
        (site / "index.html").write_text('<meta name="robots" content="noindex,follow">', encoding="utf-8")
        (site / "content").mkdir()
        (site / "content" / "research.json").write_text('{"source":true}', encoding="utf-8")
        assert any("Private directory" in e for e in audit(site)[0])
        (site / "content" / "research.json").unlink()
        (site / "content").rmdir()
        (site / "catalog.json").write_text(json.dumps({"champions": [
            {"id": "demo", "referenceFacts": {"status": "source-catalogued", "abilities": ["copy"]}}
        ]}), encoding="utf-8")
        assert any("source compilation" in e for e in audit(site)[0])
    print("Safety guard regression tests passed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--if-present", action="store_true")
    parser.add_argument("--require-site", action="store_true")
    opts = parser.parse_args()
    if opts.self_test:
        self_test()
    else:
        site = ROOT / "site"
        if not site.exists() and opts.if_present:
            print("No public site/ files staged yet. Validation only; no deploy.")
        else:
            errors, count = audit(site)
            if errors:
                for error in errors[:60]:
                    print("BLOCKER:", error, file=sys.stderr)
                if len(errors) > 60:
                    print(f"... and {len(errors)-60} more blockers", file=sys.stderr)
                sys.exit(1)
            print(f"Clean noindex public-site validation passed: {count} files.")
