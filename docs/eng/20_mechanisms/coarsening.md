# Coarsening

Note: first-pass translation of `docs/rus/20_mechanisms/coarsening.md`.

Coarsening is the mechanism for building higher-level descriptions from L0 dynamics.
Key idea: higher levels do not pause L0; they observe and update on their own clocks/frequencies.

In code, a minimal frequency-based timekeeper is implemented via “invariant tick streams”:
- `detm/run/coarsening.py`
- emits `invariant_tick` events at rational dt ratios relative to the L0 tick (`step_count`)

Persistence/analysis of coarsening streams must be implemented as separate EventBus subscribers (plugins), not inside the coarsener itself.

Canonical scaling/normalization constraints: `docs/eng/20_mechanisms/scale_axis.md`.
