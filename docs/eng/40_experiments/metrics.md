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

Log a compact time series (e.g. `E_mean(t)` over a region) and compute rFFT peaks to estimate dominant periods and their ratios.

## Flow proxies for “merging”

Track flux intensity in the interaction zone and time-to-stabilize after contact.
