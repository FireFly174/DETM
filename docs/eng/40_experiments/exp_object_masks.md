# Object masks and boundary diagnostics

Note: first-pass translation of `docs/rus/40_experiments/exp_object_masks.md`.

## Why this exists

The model exposes only fields (`E`, flows `J`, entropy proxies, `τ`), but we keep talking about “objects”, “attractors”, and “structures”.

To compare runs and build metrics, we need an **operational definition**: extract an object as a lattice region (a mask) and compute observables over that region and its boundary.

---

## How to build a mask (options)

Minimal approaches (can be combined):

1) Energy threshold
- `M = (E > mean(E) + k * std(E))`

2) Boundary via gradients
- `M = (|∇E| > θ)` as a front map; then region extraction (e.g. fill contours)

3) Activity/flow threshold
- `M = (|J| > θ)` for “alive” regions with active transport

4) Vorticity-based
- build `M` around `curl(J)` cores (if vortices/orbits are present)

In practice it is useful to keep both:
- a hard binary mask `M` (components/area),
- a soft weight field `w` (e.g. normalized energy) for weighted metrics.

---

## Mask boundary

The boundary `∂M` is used to measure exchange with the environment and to test “interface” hypotheses.
Practically:
- compute `∂M` as a morphological border of the binary mask,
- or as cells with `M=1` having at least one neighbor with `M=0`.

---

## Minimal metrics

### Geometry/identity
- `area(M)`, `r_eff` (effective radius), center-of-mass/centroid
- `n_components` and component size distribution
- shape stability: `corr(E(t), E(t+Δt))` inside `M`

### Boundary flows
- `J_boundary`: mean `|J|` on `∂M`
- `E_flux_in/out`: a proxy of energy in/out via `∂M` (using `J` direction and boundary normal)
- circulation `∮ J·dl` (orbit/closure indicator)

### Internal dynamics
- `J_inside`: mean `|J|` inside `M` (distinguishes “dead” vs “alive” objects)
- `curl_rms` inside `M`

---

## How to use this in experiments

- lifecycle: birth → stabilization → interactions → decay/transition;
- regime comparison and phase transitions (see `docs/eng/40_experiments/exp_phase_map.md`);
- transfer speed inside the object and across its boundary (see `docs/eng/40_experiments/exp_transfer_speed.md`).

Metric summary: `docs/eng/40_experiments/metrics.md`.

