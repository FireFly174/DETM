# Documentation Index (RU Canonical)

This page is an index-only entrypoint for canonical Russian documentation.

## Start Here

- Repository entrypoint: `README.md`
- Overview: `docs/rus/00_overview/README.md`
- One-pager: `docs/rus/00_overview/one_pager.md`
- Roadmap (human): `docs/rus/ROADMAP_HUMAN.md`
- Roadmap (engineering source-of-truth): `docs/rus/ROADMAP.md`
- Canonical integration contract: `docs/rus/integration_contract.md`
- Runtime/UI/viz architecture: `docs/rus/architecture.md`
- Shared docs root index: `docs/README.md`

## Текущий срез

- Проверенный локальный snapshot (2026-04-10): `python main.py --help`, `pytest -q -> 439 passed in 16.51s`
- Граница слоёв зафиксирована: `detm/*` — library-core и runtime-контракты, `detm_app/*` — orchestration/UI/transport/subscribers
- Fabric production baseline, phase-F code contour и bounded N-D migration уже закрыты как baseline
- Открытый фокус: `G-RND-01`, `MSC-02`, analytics/outerfields retention follow-up и остаточный P1 structural debt
- Важно: текущее runtime `coarsening` в `detm_app/runtime/coarsening.py` — это invariant/coarse-time stream layer, а не финальный объектный `L0 -> L1` coarsener
- Analytics read-model и multiscale catalog остаются bounded transition layers; не трактовать как финальную архитектуру

## Canonical Section Map

- `00_overview/`
- `10_model/`
- `20_mechanisms/`
- `30_architecture/`
- `40_hypotheses/`
- `50_experiments/`
- `60_limits/`
- `90_notes/`

## High-Priority Governance Notes

- Notes policy and local index: `docs/rus/90_notes/README.md`
- Book concepts single source: `docs/rus/90_notes/book_concepts_single_source.md`
- Learning model: `docs/rus/90_notes/learning_model_detm.md`
- Readout and anti-Goodhart: `docs/rus/90_notes/readout_protocol_and_antigoodhart.md`
- Source materials map: `docs/rus/90_notes/source_materials.md`

## Translation and Derivative Layers

- EN translation index: `docs/eng/README.md`
- Book framing (non-canon): `docs/book/`
- Local raw/archive/generated layer: `docs/source/`

## Policy

- RU docs are the source-of-truth for content conflicts.
- EN docs are derivative translation.
