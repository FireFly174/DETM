# Architecture overview

This document describes the current repository structure and its intended separation of concerns: formal L0 dynamics vs. runtime wrappers vs. tooling.

See also: `docs/eng/integration_contract.md`.

---

## 1) Canonical layers

### `detm/core/` — minimal primitives

Reusable components:
- lattice and neighborhood rules (as a special case of a graph)
- scalar fields and state containers
- “structural suppression” (entropy-like quantities)
- one deterministic dynamics step + base invariants

This layer must not include UI, run logging, or experiment scripts.

### `detm/runtime/` — execution + contracts + influences

This layer “packages” the core into an executable system:
- config/schema versions and state serialization
- the stable runtime API (`reset/step/digest/serialize`)
- external influences (masks/regions/external features)
- diagnostics and standard observables

Idea: dynamics stay in `detm/core/`, while contracts and wrappers live in `detm/runtime/`.

### `visualization/` — result rendering helpers

Colormaps and render helpers (used by UI/analysis layers).

### `experiments/`, `tools/` — scenarios and utilities

- `experiments/`: reproducible experiment scenarios
- `tools/`: analysis/export utilities

---

## 2) `legacy/`

`legacy/` stores historical implementations and experiments. It is useful for context and parity checks, but it is not the canon.
If `legacy/` conflicts with `docs/`, `docs/` wins.

