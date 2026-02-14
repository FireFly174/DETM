# Inertia and “mass” as a consequence of locality (hypothesis)

Note: first-pass translation of `docs/rus/40_hypotheses/inertia_mass_locality.md`.

## Idea

DETM has no explicit “mass” parameter, but stable structures can exhibit **inertial behavior**:
- they do not “jump” to a new state instantly,
- their trajectory/shape changes only under sufficiently long or coherent perturbations.

Hypothesis: inertia emerges from:
- locality of transfers,
- internal time `τ`,
- structural stability of the attractor against reconfiguration.

---

## Operational interpretation

“Mass” can be treated as **attractor resistance to reconfiguration**:
to “accelerate”/shift an object you need a sequence of local perturbations that travel through the boundary and reshape internal dynamics.

---

## Metrics

- response time to perturbations (ticks until observables/shape change);
- “break threshold”: how many local “hits” the object survives before regime change;
- shape change proxy `corr(E_before, E_after)` under the same perturbation power;
- comparison across `lambda_t` (weak vs strong asynchrony).

---

## Minimal experiments

1) Apply an “impact” on the object boundary and measure reconfiguration time.  
2) Compare the same scenario for `lambda_t ≈ 0` vs large `lambda_t`.  
3) Log `J_boundary`, `corr(E(t),E(t+Δt))`, and `t_stable` before/after the perturbation.

Related protocols:
- masks/boundaries: `docs/eng/40_experiments/exp_object_masks.md`
- transfer speed/lags: `docs/eng/40_experiments/exp_transfer_speed.md`


