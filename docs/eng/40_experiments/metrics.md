# Metrics and observables

Note: first-pass translation of `docs/rus/40_experiments/metrics.md`.

## General principles

A metric is considered valid if it is:
- reproducible under repeated runs
- stable under small parameter changes
- not dependent on a visual interpretation

---

## Core metrics (examples)

1) Energy distribution (field statistics)
2) Activity/flux intensity (integral transport activity)
3) Period (dominant oscillation period)
4) Phase coherence (synchronization measure)
5) Localization radius (energy concentration)
6) Lifetime (ticks of identity preservation)
7) Drift speed (center-of-mass changes under gradients)

---

## Regimes (phases) and phase maps

For coarse regime classification (freeze / vortex cycle / “turbulence”), use tail metrics:

- `t_stable`: time to stabilize (e.g. when `mean(|J|) < ε` for a window `W`)
- `J_tail`: tail activity `mean(|J|)` after burn-in
- `curl_rms`: RMS vorticity proxy (or any stable curl-like feature of `J`)
- spectral features: dominant rFFT peak of a compact time series (`E_mean(t)`, `signature(t)`)

Protocol: `docs/eng/40_experiments/exp_phase_map.md`.

---

## Objectness and masks

The model has no explicit “object” entity; objects are extracted diagnostically as regions where:
- `E` (and/or its derivatives) forms a stable structure
- the shape is preserved over time

Minimal mask metrics:
- object area / effective radius (`area`, `r_eff`)
- number and size of connected components (`n_components`)
- shape stability: `corr(E(t), E(t+Δt))` inside the mask
- boundary metrics: `J_boundary`, `E_flux_in/out`, circulation `∮ J·dl`

Protocol: `docs/eng/40_experiments/exp_object_masks.md`.

---

## Transfer speed, lags, and “signal speed”

Ways to estimate propagation speed:
- lag correlations: `corr(E(x0,t), E(x1,t+τ))` → `τ_max` as transfer delay estimate
- speed proxy: `v_eff = ⟨ |J| / (E + ε) ⟩` (inside the mask / on the boundary)
- orbit/period features: `T_orbit` via ring means or circulation measures

Protocol: `docs/eng/40_experiments/exp_transfer_speed.md`.

---

## Auxiliary metrics (examples)

- energy variance
- correlation functions
- spectral density over time
- invariant density at a higher level

All metrics should be computed without external semantic assumptions.

---

## Phase metric and PLV (for frequency hypotheses)

If you can define a phase `φ(t)` for a structure/domain, phase locking can be quantified via PLV:

`PLV(Ω1,Ω2) = | mean_t exp(i (φ1(t) - φ2(t))) |`

Practical “locking” criterion: `PLV > θ` over a window `W`.

## Spectral density and dominant period

Log a compact time series (e.g. `E_mean(t)` over a region, or compact scalars from `digest`/`signature`) and compute rFFT peaks to estimate dominant periods and their ratios.

## Flow proxies for “merging”

Track flux intensity in the interaction zone and time-to-stabilize after contact.

---

## Boundary “holography” (optional, hypothesis)

If you have a mask, you can test how predictive the boundary is for the interior:
- `MI(E_boundary, E_in)` or correlations between boundary and interior features
- reconstruction of `E_in` from `E_boundary` via a simple model (linear/ML, as an external analysis step)

This lives in the interpretation layer, but provides useful diagnostics for regimes and interactions.
