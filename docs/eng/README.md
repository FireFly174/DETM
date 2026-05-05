# Documentation Index (EN Translation)

This page is an index-only entrypoint for English translation docs.

## Start Here

- Repository entrypoint: `README.md`
- Overview: `docs/eng/00_overview/README.md`
- One-pager: `docs/eng/00_overview/one_pager.md`
- Roadmap snapshot (EN): `docs/eng/00_overview/roadmap_snapshot.md`
- Roadmap (RU source-of-truth): `docs/rus/ROADMAP.md`
- Integration contract (EN): `docs/eng/integration_contract.md`
- Runtime/UI/viz architecture (EN): `docs/eng/architecture.md`
- Shared docs root index: `docs/README.md`

## Current Snapshot

- Verified local snapshot (2026-04-10): `python main.py --help`, `pytest -q -> 439 passed in 16.51s`
- Stable boundary: `detm/*` is library-core/runtime contracts, `detm_app/*` is orchestration/UI/transport/subscribers
- Closed baselines: fabric production baseline, phase-F code contour, bounded N-D migration
- Current open focus lives in RU source-of-truth roadmap: `G-RND-01`, `MSC-02`, analytics/outerfields retention follow-up, residual P1 structural debt

## EN Section Map

- `00_overview/`
- `10_model/`
- `20_mechanisms/`
- `30_hypotheses/`
- `40_experiments/`
- `50_limits/`
- `90_notes/`

## Translation Scope Notes

- EN is derivative from canonical RU docs in `docs/rus/`.
- Mirror depth can lag behind RU for architecture and notes.
- For canon conflicts, use RU source-of-truth.

## Related Layers

- RU canonical index: `docs/rus/README.md`
- Book framing (non-canon): `docs/book/`
- Source archive: `docs/source/`
