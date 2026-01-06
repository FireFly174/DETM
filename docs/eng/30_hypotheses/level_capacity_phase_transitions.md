# Level capacity and phase transitions (hypothesis)

Note: first-pass translation of `docs/rus/30_hypotheses/level_capacity_phase_transitions.md`.

## Idea

“Level capacity” here is not “maximum energy”, but a **stability boundary of a regime**:
once a threshold is exceeded, the structure loses stability and transitions into a different behavior class (a phase transition).

Operationally this shows up as a change in stationary ranges of tail metrics.

---

## Transition detector (operational)

Detect a transition if within a window `[t, t+W]` metrics move into a different stable range and remain there:
- sharp drop in `corr(E(t),E(t+Δt))` (loss of shape identity),
- jump in `std(E)` or similar dispersion proxies,
- change in `J_tail` and/or circulation restructuring,
- “spectral shift”: change of dominant period/peak.

---

## Why it matters

- phase maps: locate regime boundaries and “interesting” parameter zones;
- diagnose overload / leaving the basin of attraction;
- connect to scaling (how thresholds change with lattice size `N`).

---

## Related docs

- regime phase maps: `docs/eng/40_experiments/exp_phase_map.md`
- metrics: `docs/eng/40_experiments/metrics.md`
- masks/boundaries: `docs/eng/40_experiments/exp_object_masks.md`

