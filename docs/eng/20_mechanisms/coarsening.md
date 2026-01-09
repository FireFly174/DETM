# Coarsening

Note: first-pass translation of `docs/rus/20_mechanisms/coarsening.md`.

Coarsening is the mechanism for building higher-level descriptions from L0 dynamics.
Key idea: higher levels do not pause L0; they observe and update on their own clocks/frequencies.

In code, a minimal frequency-based timekeeper is implemented via “invariant tick streams”:
- `detm/run/coarsening.py`
- emits `invariant_tick` events at rational dt ratios relative to the L0 tick (`step_count`)

Persistence/analysis of coarsening streams must be implemented as separate EventBus subscribers (plugins), not inside the coarsener itself.

Canonical scaling/normalization constraints: `docs/eng/20_mechanisms/scale_axis.md`.

### Coarsening and Mandatory Refinement

Coarsening in DETM is not optional optimization.
It is paired with a mandatory refinement mechanism that is activated
when the representability invariant (E ≤ 1) is violated.

Refinement is local, deterministic, and reversible with respect
to preserved invariants.

See: `level_scaling_refinement.md`

