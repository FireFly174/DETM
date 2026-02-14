# Baseline Tests (DETM, EN)

This document defines a minimal baseline experiment set.

Card status:
- `status`: ready_for_execution
- `artifact_status`: pending run artifacts for current milestone
- `last_reviewed`: `2026-02-14`

Goals:
- quickly validate that the research loop works end-to-end
- keep protocol details in existing `exp_*` files

## B0. Replication and determinism

Protocol:
- rerun the same config with the same seed.

Check:
- key readout artifacts match (within protocol-defined tolerance).

References:
- `docs/eng/integration_contract.md`
- `docs/eng/40_experiments/legacy_data_formats.md`

## B1. Regime phase map (core)

Protocol:
- `docs/eng/40_experiments/exp_phase_map.md`

Check:
- regimes are distinguishable by metrics, not only visuals
- transitions are observable on parameter grids

Key metrics:
- `J_tail`, `curl_rms`, `t_stable`, spectral features

## B2. Object mask and boundary

Protocol:
- `docs/eng/40_experiments/exp_object_masks.md`

Check:
- mask remains stable over observation windows
- boundary metrics are informative during interactions

## B3. Transfer and lag diagnostics

Protocol:
- `docs/eng/40_experiments/exp_transfer_speed.md`

Check:
- lag profile is interpretable and stable across seeds
- medium changes affect lag in the expected direction

## B4. Channel-assisted coupling

Protocol:
- `docs/eng/40_experiments/exp_channels.md`

Check:
- coordination acceleration appears only with channel enabled
- effect disappears when channel is removed

## B5. Density and capacity limit

Protocol:
- `docs/eng/40_experiments/exp_density.md`

Check:
- a stable-structure density limit is observable for fixed conditions

## Baseline report format

Minimum:
1. B0-B5 table with `pass/fail/inconclusive`.
2. Artifact links for each baseline item.
3. Short interpretation-risk list (what could still invalidate conclusions).
