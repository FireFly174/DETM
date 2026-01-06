# Experiment: marker scaling

Note: first-pass translation of `docs/rus/40_experiments/exp_marker_scaling.md`.

Goal: evaluate how markers/structures behave under scale changes and coarsening schedules.

## Normalization notes (important for scaling by N)

When changing lattice size `N`, comparisons are only meaningful if you explicitly fix the energy/initialization normalization. Common options:
- fix `E_total = const` (energy per cell decreases as `N` grows)
- fix `mean(E) = const` (intensive normalization; comparable “by density”)
- fix `E_total ∝ N` or `E_total ∝ N^2` (depending on the intended scaling interpretation)

Record the chosen normalization in the run `meta/config` so metrics are comparable.
