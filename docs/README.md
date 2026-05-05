# Documentation Index

This page is an index-only entrypoint for `docs/**`.

## Canon and Precedence

- Canonical source: `docs/rus/**`
- Translation layer: `docs/eng/**`
- Legal layer: `docs/legal/**` (authoritative for distribution terms)
- Non-canon framing: `docs/book/**`
- Local raw/archive/generated layer: `docs/source/**`
- Auxiliary artifacts: `docs/media/**`, `docs/uml/**`

When RU and EN differ, prefer RU canonical docs.

## Start Here

- Repository entrypoint: `README.md`
- RU overview: `docs/rus/00_overview/README.md`
- EN overview: `docs/eng/00_overview/README.md`
- RU one-pager: `docs/rus/00_overview/one_pager.md`
- EN one-pager: `docs/eng/00_overview/one_pager.md`
- RU roadmap (human): `docs/rus/ROADMAP_HUMAN.md`
- RU roadmap (engineering source-of-truth): `docs/rus/ROADMAP.md`

## Current Snapshot

- Verified local snapshot (2026-04-10): `python main.py --help`, `pytest -q -> 439 passed in 16.51s`
- Architecture boundary is stable: `detm/*` = library-core/runtime contracts, `detm_app/*` = orchestration/UI/transport/subscribers
- Closed baselines: fabric production baseline, phase-F code contour, bounded N-D migration
- Current open focus: `G-RND-01`, `MSC-02`, analytics/outerfields retention follow-up, and residual P1 structural debt
- Treat analytics read-model and current multiscale catalog as bounded transition layers, not final architecture

## Foundation Docs

- Branching policy: `docs/BRANCHING.md`
- Integration contract root: `docs/integration_contract.md`
- RU index: `docs/rus/README.md`
- EN index: `docs/eng/README.md`

## Canonical RU Core Paths

- Model: `docs/rus/10_model/`
- Mechanisms: `docs/rus/20_mechanisms/`
- Architecture: `docs/rus/30_architecture/`
- Hypotheses: `docs/rus/40_hypotheses/`
- Experiments: `docs/rus/50_experiments/`
- Limits: `docs/rus/60_limits/`
- Curated support and governance notes: `docs/rus/90_notes/`

## Derivative and Supporting Layers

- EN translation mirror: `docs/eng/`
- Book framing outputs and manifests: `docs/book/`
- Local source/archive/generated artifacts: `docs/source/`
- UML diagrams: `docs/uml/`
- Media artifacts: `docs/media/`
- Legal docs: `docs/legal/`
