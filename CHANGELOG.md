# Changelog

All notable changes to this project are documented in this file.

## [0.2.2] - 2026-02-14

- Completed documentation consistency pass before public release:
  - local markdown link check across `docs/**/*.md` is clean
  - fixed stale/broken internal references in notes/source cards
- Synchronized EN/RU documentation structure for canonical cards:
  - added EN mirrors for `50_experiments/*` and `80_limits/*`
  - added missing EN v2 sidecards for `L0..L5` deep chapters
  - added RU/EN one-pagers and updated docs navigation indexes
- Updated roadmap path references to the current post-refactor module layout.
- Release metadata bump to `0.2.2` in `pyproject.toml` and `CITATION.cff`.

## [0.2.1] - 2026-02-14

- Added explicit branching policy and workflow docs:
  - `docs/BRANCHING.md`
  - `CONTRIBUTING.md` updates for `dev/main` -> `main` release flow
- Clarified public release process and required check names.
- Moved legal docs under `docs/legal/*` and synchronized root/docs links.
- Updated dependency manifest for default launcher and experiment tooling:
  - `requirements.txt` now includes runtime UI/analysis dependencies used by default paths
- Updated third-party notices to reflect direct dependencies from both
  `pyproject.toml` and `requirements.txt`.
- Adjusted CI workflow to avoid disallowed external marketplace actions
  under repository ruleset constraints.

## [0.2.0] - 2026-02-14

- Runtime/app restructuring finalized across `detm` and `detm_app`.
- Monolithic runtime modules split into cohesive subpackages:
  - `detm/runtime/serialization/*`
  - `detm/runtime/refinement/{apply.py,pipeline/*}`
  - `detm/runtime/level_policy/*`
  - `detm_app/runtime/session/*`
  - `detm_app/runtime/ui_runtime/*`
  - `detm_app/runtime/subscribers/{trace,watch,commit,fabric}/*`
- Docs and architecture references synchronized, including UML suite.
- Canonical entrypoint remains `main.py`; legacy wrapper `detm.py` removed.
- Stabilized TCP fabric transport connect path with relay-ready handshake.
- Reduced race-window for first message delivery right after connect.
- Fix targets CI flake in:
  - `tests/test_fabric_tcp_transport.py::test_tcp_fabric_transport_auth_accepts_with_matching_key`
- Public-repo readiness package added:
  - `LICENSE`, `COMMERCIAL_LICENSE.md`, `LICENSE_FAQ.md`, `NOTICE`, `THIRD_PARTY_NOTICES.md`
  - `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `SUPPORT.md`
  - GitHub templates (`ISSUE_TEMPLATE`, PR template, `CODEOWNERS`, `dependabot`)
- License model documented as:
  - source-available non-commercial (`PolyForm-Noncommercial-1.0.0`)
  - separate commercial licensing.
