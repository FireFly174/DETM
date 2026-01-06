# Internal time (latency)

Note: first-pass translation of `docs/rus/20_mechanisms/internal_time.md`.

Internal time `τ(r,t)` is a per-cell latent state that modulates when a cell emits/advects energy.
It creates asynchronous dynamics without introducing a second global clock.

In the current implementation, internal time is advanced deterministically from local entropy and compared to an activation threshold.

## Global tick vs “proper time” of an invariant

Distinguish:
- global tick: computation index / causality order
- proper time of an object: an observable property of a stable invariant, defined through its internal period/cycle

Operational measurements:
- oscillation period in ticks (cycle length)
- relaxation time after perturbations
- phase-cycle period (if a phase is defined)

See metrics: `docs/eng/40_experiments/metrics.md`.
