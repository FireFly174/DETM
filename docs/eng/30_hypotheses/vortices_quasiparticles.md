# Orbits and vortices as quasiparticles (hypothesis)

Note: first-pass translation of `docs/rus/30_hypotheses/vortices_quasiparticles.md`.

## Idea

In DETM dynamics, persistent circulation of the flow `J` may emerge: localized regions where transport forms a long-lived closed trajectory.

Hypothesis: these structures can be treated as **quasiparticles**:
- localized,
- live much longer than random fluctuations,
- preserve parameters (direction/phase/amplitude),
- interact (merge, deflect, annihilate).

---

## “Particle-likeness” metrics

- `lifetime`: how many ticks the structure persists;
- `curl(J)` and `curl_rms`: presence/strength of vorticity;
- circulation `∮ J·dl` (how much transport “loops” around a core/boundary);
- core stability: temporal correlation of the `curl(J)` map;
- vortex center trajectory (speed/drift).

---

## Minimal measurement procedure

1) Compute `curl(J)` and find local extrema (cores).  
2) Track core position and metrics over a window.  
3) Record environment regime (parameters) to separate:
   - “accidental swirls”,
   - persistent cycles/orbits.

---

## Related experiments/metrics

- regimes and phase maps: `docs/eng/40_experiments/exp_phase_map.md`
- masks/boundaries: `docs/eng/40_experiments/exp_object_masks.md`
- transfer speed/orbit features: `docs/eng/40_experiments/exp_transfer_speed.md`
- metric summary: `docs/eng/40_experiments/metrics.md`

