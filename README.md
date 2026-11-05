# Summoner Index — clean public website distribution

This is the **public publishing destination only**. It is **not** the original MCOC research and development repository.

- The development repository `mcoc1all1/summoner-index-source` is **private**.
- The current live beta remains deployed from `mcoc1all1/summoner-index` until an explicitly approved cutover.
- This repository must contain **only public website build files in `site/`**, this README, and the small deployment guard/workflow under `.github/`.
- Do not import, mirror, or push the private source repository's Git history here.
- Don't add `content/`, `src/`, `scripts/`, `tests/`, editorial reviews, source compilation files, personal access tokens or credentials.
- All website pages must remain `noindex,follow`; beta sitemap remains empty. No AdSense scripts or advertising until explicitly authorized.

## Safe operation

This repository's GitHub Actions workflow **validates on PRs and commits** but does not deploy automatically. Even after a website-only `site/` snapshot arrives, publishing requires a manual workflow run with `publish_preview` explicitly enabled and the repository's Pages source configured for **GitHub Actions**.

The private source repository will build and validate the website before copying `dist/` output to `site/` using a narrowly scoped publish credential. No cross-repository deployment credential should be committed to this public repository.

Until the custom domain and final `summoner-index` publishing cutover are approved, this repository's independent preview URL is `https://mcoc1all1.github.io/summoner-index-site/`. It is **not** the live domain or the existing website.

This technical validation does not establish copyright clearance, gameplay testing or AdSense eligibility.
