# Research Program (DETM, EN)

This file defines a research-program layer on top of existing protocols.

Card status:
- `status`: active (doc contract)
- `execution_status`: pending code contour (`F-01..F-03` are `todo` in roadmap)
- `last_reviewed`: `2026-02-14`

Purpose:
- connect hypotheses and experiments into one execution map
- define minimal artifact and acceptance requirements
- reduce planning overhead without duplicating protocol details

Scope:
- this document does not replace `exp_*` files
- formulas/procedure details stay in protocol documents

## Source-of-truth references

- Hypotheses: `docs/eng/30_hypotheses/hypotheses.md`
- Shared metrics: `docs/eng/40_experiments/metrics.md`
- Protocols: `docs/eng/40_experiments/exp_*.md`
- Interpretation limits: `docs/eng/50_limits/limits.md`

## Hypothesis -> experiment matrix

| Hypothesis | Primary protocol | Supporting protocol | Key metrics |
|---|---|---|---|
| H1, H4, H12 | `docs/eng/40_experiments/exp_phase_map.md` | `docs/eng/40_experiments/exp_object_masks.md` | `J_tail`, `curl_rms`, phase/stability |
| H2, H11, H17 | `docs/eng/40_experiments/exp_marker_scaling.md` | `docs/eng/40_experiments/exp_phase_map.md` | cross-scale transferability, metric drift |
| H3, H8, H14 | `docs/eng/40_experiments/exp_transfer_speed.md` | `docs/eng/40_experiments/exp_channels.md` | lag correlations, dominant frequencies, latency proxies |
| H5, H6 | `docs/eng/40_experiments/exp_gradient.md` | `docs/eng/40_experiments/exp_object_masks.md` | shape/period preservation, drift, perturbation robustness |
| H7 | `docs/eng/40_experiments/exp_torus.md` | `docs/eng/40_experiments/exp_transfer_speed.md` | mobility, shape and period retention |
| H9 | `docs/eng/40_experiments/exp_channels.md` | `docs/eng/40_experiments/exp_transfer_speed.md` | no transfer without prepared medium |
| H10 | `docs/eng/40_experiments/exp_density.md` | `docs/eng/40_experiments/exp_phase_map.md` | invariant density capacity limit |
| H13, H15, H16 | `docs/eng/40_experiments/exp_phase_map.md` | `docs/eng/40_experiments/exp_object_masks.md` | PLV/spectral/boundary-flow coupling signals |

## Minimal artifact package per series

1. Run metadata: `config`, `seed`, runtime version.
2. Compact readout time series (`metrics.csv` or equivalent).
3. Final state snapshot (`final_state.npz` or equivalent).
4. Series aggregate (`summary` table across seeds/params).

Recommended:
- include explicit links to target `H*` and used `exp_*` protocol in metadata.

## Hypothesis acceptance definition (DoD)

A hypothesis is considered supported (within model scope) when:
1. the effect is reproducible across multiple seeds
2. the effect remains under moderate parameter variation
3. a falsification path is explicitly defined
4. artifacts allow independent rerun without manual context recovery

## What to avoid in this layer

- introducing new physical claims on top of readout
- replacing hypothesis criteria with visual appeal
- mixing runtime refactoring status with scientific conclusion in one readout
