# DETM — Discrete Entropy-Time Model

## Short description

DETM is a research discrete dynamics model on a lattice. It is designed to study the emergence of stable localized structures (“invariants”) from strictly local transport rules, without encoding objects, goals, or global coordination.

The model combines:
- local transport of a scalar quantity (“energy”)
- structural (entropy-like) suppression
- internal time (latency)

The main focus is not single-cell behavior but emergent regimes and structures that appear under coarsening.

---

## Relation to DAGM (generalization)

The project uses a two-level description:
- **DETM**: concrete lattice implementation (2D lattice + fields `E`, `S`, `τ`)
- **DAGM**: minimal abstract graph formulation (nodes/edges/capacities/delays), where a lattice is a special case

See: `docs/eng/10_model/dagm_core.md`.

---

## What is studied

- when local rules produce stable structures
- what mechanisms ensure longevity and separability
- how internal asynchrony affects stability and scaling
- whether there are limits of density and throughput of such structures

---

## What the model does NOT claim

DETM is not a physical/biological/cognitive theory. Any analogies outside the formal dynamics are treated as external interpretation and are not part of the canon.

---

## Documentation structure

- `10_model`: formal specification
- `20_mechanisms`: mechanisms of emergent dynamics
- `30_hypotheses`: hypotheses to test
- `40_experiments`: protocols and metrics
- `50_limits`: limits and forbidden interpretations
- `90_notes`: drafts and archives
- `architecture.md`: repository and module overview

Current EN parity:
- core model/mechanisms/hypotheses/experiments/limits cards are mirrored from `docs/rus`.
- architecture deep-cards and long-form research notes remain canonical in Russian.

---

## Project status

The project is in an active research stage. Results are preliminary and must be validated by reproducible runs.

Source-of-truth roadmap is maintained in Russian:
- `docs/rus/ROADMAP.md`
- `docs/rus/ROADMAP_HUMAN.md`

English snapshot:
- `docs/eng/00_overview/roadmap_snapshot.md`

Development flow:
- active development branch: `dev/main`
- release branch: `main`
- policy: `docs/BRANCHING.md`

One-page overview:
- `docs/eng/00_overview/one_pager.md`
