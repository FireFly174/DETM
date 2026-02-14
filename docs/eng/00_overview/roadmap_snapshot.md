# Roadmap Snapshot (EN)

Updated: 2026-02-14

This page is an English orientation snapshot.
Canonical planning and statuses are maintained in:
- `docs/rus/ROADMAP.md` (source-of-truth)
- `docs/rus/ROADMAP_HUMAN.md` (human-readable projection)

## Current execution model

- Development branch: `dev/main`
- Release branch: `main`
- Release tags are created from `main`
- Full branching policy: `docs/BRANCHING.md`

## Current status (high level)

- Baseline runtime/app migration is complete.
- Fabric production-baseline track (`G-FAB-01..05`) is complete.
- Main open technical focus:
  - `WS-F`: learning code contour (`F-01..F-03`)
  - `WS-G-ND`: N-dimensional runtime migration (`G-ND-01..03`)
  - residual runtime/app structural debt (P1)

## Public packaging track (non-blocking)

The following tasks are planned as public-facing quality improvements:

- `PUB-01`: add 3-5 curated demo assets to `docs/book/assets` and wire them into `README.md`
- `PUB-02`: define 2-3 canonical visual presets with reproducible commands
- `PUB-03`: create one-page project overview (RU/EN)
- `QLT-01`: improve runtime code-level docstrings and type hints
- `DAGM-01`: prepare RFC for a separate general-graph DAGM runtime track

These tasks improve accessibility and onboarding but do not replace core priorities in `WS-F` and `WS-G-ND`.
