# DETM core model specification

Note: this is a first-pass translation of `docs/rus/10_model/model_core.md`. The RU version is canonical for formulas/notation.

---

## 1) Overview

DETM (Discrete Entropy‑Time Model) is a discrete dynamical system on a regular 2D lattice.
The goal is to study stable localized invariant structures that arise from local rules only.

DETM is a concrete lattice instance of the more general DAGM formulation:
`docs/eng/10_model/dagm_core.md`.

---

## 2) Space and time

### Space

The system is defined on a 2D lattice Ω of size `N×N`.
Each cell is identified by a position `r ∈ Ω`.

Locality: each cell interacts only with its neighbors (the neighborhood type is specified separately).

Boundary conditions can be:
- fixed
- open
- periodic (torus topology)

### Time

Time is discrete: `t = 0, 1, 2, ...`.
All updates are computed relative to the global tick.

Additionally, each cell may have its own internal time/latency `τ(r,t)` that modulates local responses without changing the global tick.

---

## 3) State variables

Per cell `r` at time `t`:
- energy `E(r,t) ∈ [0,1]`
- structural suppression / entropy proxy `S(r,t) ≥ 0`
- internal time / latency `τ(r,t) ≥ 0`

Auxiliary fields may be introduced for convenience, e.g. a chemical potential `μ(r,t)` and its zero-mean version `μ_eff`.

---

## 4) Flows

Energy transport between neighboring cells is local and constrained.
A conductivity parameter `κ > 0` scales the base flow strength.

Effective flows are suppressed by:
- higher `S(r,t)`
- higher `τ(r,t)` (via activation/latency rules)

---

## 5) Update rule (high level)

At each global tick:
- compute `S` from energy deviations and neighborhood heterogeneity
- compute potentials and conductances
- advance internal time `τ` and determine which cells are “active” for emission
- apply local flows and update energy conservatively

The rule should:
- conserve total energy (subject to boundary choice)
- remain strictly local
- prevent unlimited propagation of perturbations

---

## 6) Invariants (operational definition)

An invariant structure is a localized regime that remains stable in time and under moderate perturbations.
Operational signs:
- spatial localization
- stable internal period/phase
- phase coherence
- robustness to local influences

See: `docs/eng/20_mechanisms/invariants.md`.

