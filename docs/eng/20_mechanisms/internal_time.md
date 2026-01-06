# Internal time `τ` (latency)

Note: first-pass translation of `docs/rus/20_mechanisms/internal_time.md`.

Internal time `τ(r,t)` is a per-cell latent state that modulates when a cell can propagate influence to its neighbors.
It creates asynchronous dynamics without introducing a second global clock:
- the global tick defines causality/computation order;
- `τ` shapes local response delay and the effective propagation speed of changes across the lattice.

In the current implementation, internal time is advanced deterministically from local entropy and compared to an activation threshold.

## `λ_t` (entropy → delay coupling)

`lambda_t` controls how strongly local entropy/roughness contributes to delay:
- small `lambda_t` → closer to synchronous dynamics;
- large `lambda_t` → more heterogeneous `τ` and “slow zones”.

## Global tick vs “proper time” of an invariant

Distinguish:
- global tick: computation index / causality order
- proper time of an object: an observable property of a stable invariant, defined through its internal period/cycle

Operational measurements:
- oscillation period in ticks (cycle length)
- relaxation time after perturbations
- phase-cycle period (if a phase is defined)

## Diagnostics

Useful observables:
- distribution/entropy of the `τ` field
- lag correlations between neighboring points in `E(t)` (a proxy for “signal speed”)
- how stabilization time and tail activity change with `lambda_t`

See metrics: `docs/eng/40_experiments/metrics.md`, experiments: `docs/eng/40_experiments/exp_transfer_speed.md`.
