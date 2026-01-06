# Transfer speed and lag diagnostics

Note: first-pass translation of `docs/rus/40_experiments/exp_transfer_speed.md`.

## Goal

Estimate how fast **influence propagates** (energy / field changes) inside an object and across its boundary.
This is useful for:
- diagnosing stable structures (static vs dynamic attractor),
- testing the role of `τ` as a local causality / propagation-speed limiter,
- building regime phase maps.

Use together with mask extraction: `docs/eng/40_experiments/exp_object_masks.md`.

---

## Method A: lag correlations (transfer delay proxy)

1) Choose a reference point/region inside the object (center-of-mass, max `|J|`, vortex core).  
2) For neighbor points `x1`, compute:
   - `corr(E(x0,t), E(x1,t+τ))` over a time window,
   - `τ_max` where correlation is maximal.
3) Interpret `τ_max` as an estimate of transfer delay between `x0` and `x1`.

Note: this is a proxy, not a physical “speed”. The key is comparability across regimes/parameters.

---

## Method B: flow-based speed proxies

Minimal speed proxy from fields:

- inside the object:
  - `v_eff = ⟨ |J| / (E + ε) ⟩_mask`
- on the boundary:
  - `v_boundary = ⟨ |J| / (E + ε) ⟩_∂mask`

where `ε` is a small stabilizer.

---

## Optional: orbits and periodicity

If circulation is present:
- compute circulation `∮ J·dl` (around a contour / along the object boundary);
- estimate orbit period `T_orbit` via ring means (`ring_means`) and rFFT.

---

## Minimal artifacts

- run config + seed;
- compact series: `E_mean(t)`, `mean(|J|)(t)`, optionally `signature(t)`;
- aggregated metrics: `τ_max` profile, `v_eff`, `J_tail`, `curl_rms`.

Metric summary: `docs/eng/40_experiments/metrics.md`.

