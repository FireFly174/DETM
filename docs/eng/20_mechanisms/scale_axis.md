# Level scale axis and energy normalization

Note: first-pass translation of `docs/rus/20_mechanisms/scale_axis.md`.

This page fixes canonical constraints for multi-level scaling/coarsening. The current repo focuses on L0, but these rules matter for future compatibility and diagnostics.


### Linear Scaling of Space and Time

In DETM, spatial and temporal scaling are strictly coupled.
Scaling space by factor k implies scaling time resolution by factor k.

This coupling is enforced through level transitions and energy normalization.
Levels differ only by representational scale, not by physical laws.

See: `level_scaling_refinement.md`


## 1) Normalization invariant

At any level and any location:
- `E ∈ [0, 1]`

Forbidden:
- summing energy when going `L → L+1`;
- allowing `E > 1` on any level;
- mixing “normalized energy” with a “scale measure” inside dynamics.

## 2) Level as a real coordinate

Treat level as a real coordinate:
- `L ∈ ℝ` (e.g. `L=0.16`, `L=0.32`, `L=1.24`)

## 3) Coarsening aggregator examples

Use a normalized aggregator that keeps `E ∈ [0, 1]`.

Examples:
- saturating product: `E_{L+1} = 1 - ∏ (1 - E_L)`
- logit-normalization (preferred): average logits, then invert back

Related docs:
- coarsening overview: `docs/eng/20_mechanisms/coarsening.md`



