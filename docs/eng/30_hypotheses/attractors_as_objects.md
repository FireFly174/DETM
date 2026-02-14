# Attractors as emergent “objects”

Note: first-pass translation of `docs/rus/40_hypotheses/attractors_as_objects.md`.

## Operational definition

DETM does not define “objects” as explicit entities. The state consists of fields `E`, flows `J`, and auxiliary maps (`τ`, suppression proxies, etc.).

Operationally, an “object” is a **stable local dynamical regime** (an attractor) on a lattice region:
- shape/structure persists over a time window;
- the object can be either “dead” (no transport) or “alive” (internal circulation).

---

## Two baseline classes

### Type 1: static (freeze)

- `J ≈ 0` (transport fades),
- `E(t)` becomes nearly constant (up to noise),
- the object “freezes” into a configuration.

### Type 2: dynamic (limit cycle)

- `E` shape is stable,
- `J(t)` does not vanish: persistent circulation/vortices,
- transport continues inside while the overall shape looks stationary.

---

## Minimal detection metrics

- shape stability: `corr(E(t), E(t+Δt))` inside the object mask;
- tail activity: `mean(|J|)` after burn-in;
- vorticity: `curl_rms(J)` and/or persistent `curl(J)` cores;
- closure: `div(J) → 0` as a “no leakage” proxy (when applicable);
- geometry: mask area/radius, number of connected components.

Masks/boundaries: `docs/eng/40_experiments/exp_object_masks.md`.

---

## Lifecycle (for logging)

1) birth (local concentration, gradients/flows grow);  
2) stabilization (shape autocorrelation rises, “noise” drops);  
3) life (static or dynamic);  
4) transition/decay (under external perturbations or parameter changes).

---

## Related hypotheses and experiments

- regimes and phase maps: `docs/eng/40_experiments/exp_phase_map.md`
- transfer speed / lags: `docs/eng/40_experiments/exp_transfer_speed.md`
- metric summary: `docs/eng/40_experiments/metrics.md`


