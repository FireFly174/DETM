# DETM core rewrite checklist

Note: first-pass translation of `docs/rus/90_notes/rewrite_checklist.md`.

This is a consolidated list of required rules and interpretation constraints used when rewriting `detm/core/` and `detm/runtime/`.

Key constraints:
- lattice is 2D `N×N`, local interactions only; boundary can be fixed/open/periodic
- global discrete ticks `t = 0, 1, ...`
- per-cell internal time `τ(r,t) ≥ 0` modulates response but not global time
- energy `E(r,t) ∈ [0,1]` with conserved total (subject to boundary)
- structural suppression `S(r,t) ≥ 0` grows with deviation/heterogeneity and limits transport
- local flows scale with conductivity `κ > 0` and are suppressed by `S` and `τ`
- invariants are localized, stable over time, have stable period and robustness to perturbations
- no physical/cosmological/cognitive claims in the canon

When implementation diverges from the canon, fix either code or docs and remove contradictions.

## Rewrite checklist status (current repo)

- [x] 2D lattice `N×N`, local neighbourhoods, boundary conditions (currently `periodic|open`).
- [x] Energy `E(r,t) ∈ [0,1]` with conserved transport update (plus optional `energy_bounds` clamp).
- [x] Structural suppression `S(r,t)` derived from local deviation + heterogeneity.
- [x] Internal time `τ(r,t)` and its activation-threshold mechanism.
- [x] Local fluxes with conductivity `κ` and entropy/time suppression.
- [x] Continuity-style update (state minus outgoing flux plus incoming flux).
- [x] Operational observables for invariants: `digest/signature` and a minimal `detect_attractors` detector.
- [x] Interpretation constraints: see `docs/eng/50_limits/limits.md`.

Quick pointers:
- lattice/boundary: `detm/core/fields.py`
- reference dynamics: `detm/core/entropy.py`
- backends: `detm/runtime/backends/numpy_backend.py`, `detm/runtime/backends/torch_backend.py`
- runtime API: `detm/runtime/api/*`
