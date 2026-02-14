# Regime Transition Tests (DETM, EN)

This document defines transition-focused test scenarios.

Card status:
- `status`: ready_for_execution
- `artifact_status`: pending transition-series artifacts
- `last_reviewed`: `2026-02-14`

It extends baseline (`01_baseline_tests.md`) and reuses existing `exp_*` protocols.

## T0. Stable -> Oscillatory

Idea:
- move from low-activity state to sustained cyclic dynamics.

Protocol base:
- `docs/eng/40_experiments/exp_phase_map.md`

Transition signals:
- increasing `J_tail` with retained structural coherence
- stable dominant spectral peak appears

## T1. Oscillatory -> Turbulent/Chaotic

Idea:
- increase parameter load until stable cycle degrades.

Protocol base:
- `docs/eng/40_experiments/exp_phase_map.md`
- `docs/eng/40_experiments/exp_density.md`

Transition signals:
- higher metric variability
- loss of reproducible dominant period

## T2. Structured -> Drift under Gradient

Idea:
- apply weak gradient and test regime change with identity retention.

Protocol base:
- `docs/eng/40_experiments/exp_gradient.md`
- `docs/eng/40_experiments/exp_object_masks.md`

Transition signals:
- measurable centroid drift under controlled deformation
- no immediate structural collapse

## T3. No Channel -> Channel-Assisted Coupling

Idea:
- compare no-channel and low-latency-channel regimes.

Protocol base:
- `docs/eng/40_experiments/exp_channels.md`
- `docs/eng/40_experiments/exp_transfer_speed.md`

Transition signals:
- lag/coordination-time reduction only in channel regime

## T4. Mobility under Periodic Topology

Idea:
- validate object-like mobility under torus topology.

Protocol base:
- `docs/eng/40_experiments/exp_torus.md`

Transition signals:
- sustained displacement with period/shape retention

## Minimal transition-test design requirements

1. Explicit `before` and `after` regimes (A vs B).
2. Explicit transition lever (what parameter/control changed).
3. Observable metrics that separate A from B.
4. Negative-control scenario where transition must not occur.

## Output artifact for each T*

- transition lever description
- `before/after` metrics table
- status: `confirmed`, `not_confirmed`, `inconclusive`
- links to used base protocol (`exp_*`) and run artifacts
