# Invariant structures

Note: first-pass translation of `docs/rus/20_mechanisms/invariants.md`.

## Definition

An invariant structure is a stable localized configuration of dynamics that keeps its identity over time and under moderate perturbations.

Invariants are not encoded explicitly and are not hard-coded as initial conditions. They arise via self-organization.

---

## Characteristic properties

- spatial localization
- stable internal period
- phase coherence
- robustness to local impacts

---

## Invariants as “objects”

Invariants can display object-like behavior:
- preserve shape while moving
- react to parameter gradients
- interact with other invariants

They are not particles and do not have mass/trajectories in the physical sense.

---

## Existence bounds

Invariants exist only within certain parameter ranges. Outside those ranges they:
- decay
- lose periodicity
- dissolve into background noise

This makes it possible to explore “stability regions” experimentally.

---

## Energy Representation Invariant

The DETM model enforces a strict representability invariant:

E ∈ [0;1]

This is not a physical threshold, but a limit of the representation level.
Violation of this invariant triggers mandatory local refinement.

See: `level_scaling_refinement.md`

