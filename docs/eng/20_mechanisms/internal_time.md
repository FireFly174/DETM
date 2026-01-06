# Internal time (latency)

Note: first-pass translation of `docs/rus/20_mechanisms/internal_time.md`.

Internal time `τ(r,t)` is a per-cell latent state that modulates when a cell emits/advects energy.
It creates asynchronous dynamics without introducing a second global clock.

In the current implementation, internal time is advanced deterministically from local entropy and compared to an activation threshold.

