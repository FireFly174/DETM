# Public Release Checklist

This file captures the remaining steps to make the repository public safely.

## Repository Content Hygiene

- [x] Full test suite passes (`pytest -q`).
- [x] Architecture docs synced with current code layout.
- [x] UML set regenerated and linked from docs.
- [x] No obvious plaintext credentials detected by basic grep scan.
- [x] Standard community files added:
  - `LICENSE`
  - `CONTRIBUTING.md`
  - `CODE_OF_CONDUCT.md`
  - `SECURITY.md`
  - `SUPPORT.md`
  - issue/PR templates
  - `CODEOWNERS`
  - `CHANGELOG.md`
  - `CITATION.cff`

## Manual GitHub Settings (Before Visibility Switch)

- [ ] Enable GitHub Security Advisories.
- [ ] Configure branch protection for `main`:
  - required status checks (`CI`, `torch-tests`)
  - block force-push
  - require PR review for protected branches (if desired)
- [ ] Add repository topics and short public description.
- [ ] Add Social Preview image.
- [ ] Decide whether Discussions should be enabled.
- [ ] Verify default issue labels and milestones.
- [ ] Confirm release notes for tags:
  - `v0.1.9`
  - `v0.2.0`

## Optional Before Public

- [ ] Add a minimal roadmap badge or status badge to `README.md`.
- [ ] Add pinned example command outputs/screenshots in docs.
- [ ] Publish first GitHub Release based on `v0.2.0`.
