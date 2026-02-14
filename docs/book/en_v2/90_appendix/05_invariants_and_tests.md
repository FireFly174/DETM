# Invariants and tests

This section keeps the framework operational.
Its goal is to prevent the language from degrading into slogans.

## 1) KPI contour transparency test

Canonical honest KPI sentence:

> We intentionally optimize X and accept Y losses.

If Y cannot be stated explicitly,
KPI usually functions as self-deception or power instrument.

Checklist:

1. What exactly is optimized (which axis)?
2. Which losses are accepted in exchange?
3. What time horizon carries the bill?
4. What field readout must change besides the report number?
5. Where is the applicability boundary for this KPI?
6. Who gains and who pays, and how is that verified?
7. How does this KPI map to basis viability (L0)?

## 2) Anti-Goodhart test: report <-> cost coupling

Rule:

If report is decoupled from real cost/pain,
system trains reward hacking.

Operational tests:

- Can metric be decomposed to observables?
- Is price transfer visible (errors, risk, burnout, quality debt)?
- Is there a stop/rebuild mechanism when metric becomes target?

## 3) Rule/decision decomposition as optimization function

For any rule, KPI, incentive, or process, decompose:

1. objective function (what is really optimized),
2. constraints (what is forbidden/costly),
3. readout (where success is claimed),
4. applicability boundary,
5. price distribution and lag.

Output should identify:

- whose basis is protected,
- whose basis is sacrificed (often on hidden credit).

## 4) Presence theater test (schedule vs effect)

Common projection error:
compensation and control drift to attendance/presence instead of outcome.

Symptoms:

- time-in-place becomes target,
- report discipline grows,
- action-effect coupling degrades,
- imitation becomes rational.

Schedule can be useful.
It becomes harmful when it cannot be adapted to observed reality.

## 5) Prediction boundary: predict regimes, not persons

Framework target is regime diagnostics:
price gradients, feedback failure zones, transition likelihood.

It is usually valid for distributions and contour behavior,
not for deterministic individual trajectories.

## 6) Repository-level verification linkage

Map conceptual invariants to repo checks:

- reproducible headless runs (`catalog.json`, `metrics.csv`, `summary.json`, `final_state.*`),
- trace continuity and subscriber consistency,
- metric/counter-metric coherence,
- no forbidden cross-layer dependencies from `detm/*` into app/UI layers.

## 7) Minimal release gate for architecture changes

Before tagging a release with architecture impact:

1. invariants documented,
2. changed contracts reflected in docs,
3. tests for changed boundaries pass,
4. migration artifacts (if any) are clearly marked.

If these are missing, delay release and treat state as transition draft.
