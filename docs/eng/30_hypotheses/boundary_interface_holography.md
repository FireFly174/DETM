# Boundary as an interface and “holography” (hypotheses)

Note: first-pass translation of `docs/rus/30_hypotheses/boundary_interface_holography.md`.

## Boundary as an interaction interface

Due to locality of DETM rules, external influence can enter an “object” **only through the boundary** of the region we extract via a mask.

Intuition:
- from outside, we can change evolution conditions (environment parameters / influences);
- internal structure can only reorganize via local transfer cascades;
- therefore the boundary is the natural interaction “port” between an object and its environment.

Practical implication for future higher levels (L+1): if we want to “control an object”, that control should be expressed as boundary conditions / boundary stimuli, not direct edits of internal state.

---

## Minimal boundary metrics

Given a mask `M` and its boundary `∂M`, useful features include:
- `J_boundary`: mean `|J|` over `∂M`;
- proxy `E_flux_in/out` across `∂M` (in/out exchange);
- `|∇E|` on the boundary as interaction/front markers;
- circulation `∮ J·dl` (transport closure).

Mask extraction: `docs/eng/40_experiments/exp_object_masks.md`.

---

## Boundary “holography” (strong version, hypothesis)

Hypothesis: **the object’s internal state is largely accessible from its boundary**.
This is not physical holography; it is an operational statement about predictability:

- predict (some of) `E_in` from `E_boundary`;
- predict the future behavior from boundary signals;
- control is possible via boundary conditions.

---

## How to test (practically)

1) Extract object and boundary (mask + `∂M`).  
2) Compute `MI(E_boundary, E_in)` or correlations between features (start with aggregates/projections).  
3) Try reconstructing `E_in` from `E_boundary`:
   - linear regression / simple model as a sanity check,
   - ML as an external layer (beyond L0).

---

## Related experiments and metrics

- masks and boundaries: `docs/eng/40_experiments/exp_object_masks.md`
- transfer speed / lags: `docs/eng/40_experiments/exp_transfer_speed.md`
- metric summary: `docs/eng/40_experiments/metrics.md`

