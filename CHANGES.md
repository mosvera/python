# Changes

Chronological per-phase log for `mosvera` (Python). Newest entries on top.
The rich "why/how" for family-wide work lives in `docs/narrative/` in the
`niclydon/mosvera` repository; entries here are the scannable index.

---

## 2026-10-27 — 0.1.3 published to PyPI

- `mosvera` 0.1.3 (wheel and sdist) published to PyPI. The release workflow
  had been failing at the trusted-publishing token exchange because no
  publisher was registered for this repo; with the publisher registered
  (repository `python`, workflow `release.yml`, environment `pypi`), the
  same workflow ran green end to end. No stored secret is involved.
- Dependabot config added (PR #2), CodeQL scanning added (PR #5), and the
  GitHub Actions bumps to checkout 7 and setup-python 7 merged (PRs #4 and
  #3; #3 needed a manual rebase where the two bumps edited the same
  workflow lines).

Family record:
`docs/narrative/2026-10-27-public-face-and-the-0-1-3-release-train.md` in
`niclydon/mosvera`.

---

## 2026-10-20 — OB-59048 parity fix, version 0.1.3

PR #1 (commit `e7505ec`) ported the OB-59048 registry-loader fix from the
TypeScript loader: a registry document whose file name matches its kind
pattern (`<kind>.mosvera.json`) could be skipped during load. The loader
now applies a kind-prefix guard, with a regression test that loads a
kind-named document alongside a regular one. Version bumped to 0.1.3; the
suite passes on Python 3.10 through 3.13.

---
