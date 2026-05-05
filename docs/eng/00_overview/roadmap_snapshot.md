# Roadmap Snapshot (EN)

Updated: 2026-04-10

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
- Phase-F code contour (`F-01..F-03`) is complete.
- Bounded N-D runtime migration (`G-ND-01..03`) is complete.
- Verified local snapshot: `python main.py --help`, `pytest -q -> 439 passed in 16.51s`
- Main open technical focus:
  - `G-RND-01`: formal `local-first + validation-sync` R&D track
  - `MSC-02`: BridgeRecordSource + hot transport / trajectory-store contract follow-up
  - analytics/outerfields retention follow-up
  - residual runtime/app structural debt (P1)

## Public packaging track (non-blocking)

The following tasks are planned as public-facing quality improvements:

- `PUB-01`: done; curated reproducible demo/readout assets are wired into `README.md` and `docs/media`
- `PUB-02`: done; canonical visual presets live in `experiments/12_public_visual_presets`
- `PUB-03`: done; RU/EN one-page project overview is synchronized with the current roadmap and launch commands
- `QLT-01`: improve runtime code-level docstrings and type hints
- `DAGM-01`: prepare RFC for a separate general-graph DAGM runtime track

These tasks improve accessibility and onboarding but do not replace canonical priorities in the RU roadmap source-of-truth.
