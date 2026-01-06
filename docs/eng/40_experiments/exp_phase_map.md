# Regime phase map

Note: first-pass translation of `docs/rus/40_experiments/exp_phase_map.md`.

## Goal

Build a **regime map** (phase diagram) of DETM in the parameter space
`kappa/alpha/beta/gamma/lambda_t` to:
- locate stable structures/attractors;
- distinguish “freeze” vs “live” dynamics quantitatively;
- have a baseline for comparing versions/backends and for orchestration.

---

## Parameters and fixed conditions

Environment parameters:
- `kappa` (conductivity),
- `alpha` (gradient sensitivity),
- `beta` (pull towards `E_level`),
- `gamma` (collectivity/suppression),
- `lambda_t` (asynchrony via `τ`).

UI/trace aliases: `a,b,g,k,t` = `alpha,beta,gamma,kappa,lambda_t`.

Fix and record (per run):
- lattice size `N` and `boundary`;
- `E_level` and initialization (marker/cross/noise);
- influence rule (if any) and `seed`;
- run length and burn-in (ticks to ignore).

---

## Regime metrics

Recommended minimal metric vector (computed on the tail after burn-in):
- `t_stable`: time-to-stabilize (or `None` if it does not stabilize);
- `J_tail = mean(|J|)` on the tail;
- `curl_rms(J)` (or another stable vorticity proxy);
- basic field stats: `mean/std` for `E`, `τ`, `S`;
- objectness: object size/count from a mask (see `docs/eng/40_experiments/exp_object_masks.md`);
- spectral features: dominant peak of `E_mean(t)` or `signature(t)` (if you log digest/signature).

---

## Regime labels (draft)

A practical (improvable) classification:

- **Freeze**: `J_tail → 0`, stable `E` shape, low `curl_rms`.
- **Vortex cycle / dynamic attractor**: stable `E` shape, but `J_tail` and/or `curl_rms` remain non-trivial.
- **Long-lived/chaotic dynamics**: no stabilization within the horizon; metrics drift/oscillate; spectrum is broader.

Boundaries are typically fuzzy, so keeping the raw metrics is as important as any label.

---

## Protocol

1) Pick a 1D/2D slice (start with 2 parameters; keep others fixed).  
2) Run a grid sweep with multiple `seed` per point.  
3) For each run:
   - save config/seed,
   - log compact series (`E_mean(t)`, `mean(|J|)(t)`, `signature(t)`),
   - compute tail metrics.
4) Aggregate over seeds:
   - mean/quantiles of metrics,
   - fraction of “successful” runs (stable and repeatable regime).
5) Visualize:
   - metric heatmaps over the grid,
   - PCA/clustering on the metric vectors.

---

## Notes

- Comparing regimes across different `N` requires explicit normalization (see `docs/eng/40_experiments/exp_marker_scaling.md`).
- For reproducibility: same seed + same influence sequence → same signature/metrics.
- If you apply external influences, separate “environment regime” from “scenario response” (use the same influence sequence across the grid).

