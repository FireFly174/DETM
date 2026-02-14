<a id="nav-cheatsheet"></a>
# Navigation cheat sheet (S-T-C)

Use short codes for direct search in the compiled book.

## 1) Core diagnostic fork: breadth or depth

Rule:

- **Depth** when readout is unstable or any option yields same trajectory.
- **Breadth** when readout is stable and you optimize within current boundaries.

Pseudo-flow:

```text
if readout unstable or trajectory invariant under options:
    go_depth()   # L3 -> L1 -> L0
else:
    go_breadth() # mostly L2-L3
```

Quick symptom map:

- "Any decision gives same failure" -> `L1-C2`, then `L0-C1` / `L0-C6`
- "Metrics up, reality down" -> `L3-C1`, `L3-C6`, then `L5-C6`
- "No shared reality axis" -> `L3-C7`, then `L2-C5` / `L4-C7`
- "No next step" -> `L1-C2`; if still blind, descend to L0

## 2) Scene codes (`Sx`)

- `S1`: person
- `S2`: family/close network
- `S3`: society/game
- `S4`: organization
- `S5`: state/institutions

## 3) Theme codes (`Ty`)

- `T1`: pause/stop
- `T2`: refusal/exit
- `T3`: heroism/overspend
- `T4`: obligation reduction
- `T5`: quarantine
- `T6`: feedback restoration
- `T7`: axis/interpretation control

## 4) Combined scene-theme search (`Sx/Ty`)

Examples:

- `S4/T6` -> organization-level feedback failure and restoration
- `S1/T3` -> personal heroism overspend
- `S5/T7` -> institutional axis-control conflict

## 5) Operator search (`Lx-Cn`)

### L0 (existence operators)

`L0-C1..L0-C7`:
stop, refusal signal, overspend diagnosis, obligation reduction,
quarantine, feedback restoration, report-game exit.

### L1 (action/readout operators)

`L1-C1..L1-C7`:
minimal operation, minimal readout, cycle reduction,
parallelism reduction, incident review without punishment,
recovery windows, done=verified.

### L2 (narrative/role operators)

`L2-C1..L2-C7`:
blame mode, hero legitimation, stop taboo, refusal normalization,
frame change, observation taboo, explanation-over-experiment.

### L3 (metric/rule operators)

`L3-C1..L3-C7`:
metric-as-sensor, heroism incentive,
capacity-aligned commitments, stop rules,
error-cost return, anti-imitation, axis policy.

### L4 (institution operators)

`L4-C1..L4-C7`:
institutional stop rights, truth/refusal protection,
heroism institutionalization, legitimate de-scope,
anti-capture quarantine, honest feedback institution,
axis governance institution.

### L5 (boundary/transition operators)

`L5-C1..L5-C7`:
stop boundary, mass-refusal transition,
heroism bifurcation, capacity boundary,
cascade boundary, feedback boundary,
basis rebasing.

## 6) Practical navigation pattern

1. Search by `Sx/Ty` to get context.
2. Jump to first operator `Lx-Cn`.
3. Execute one change.
4. Validate readout.
5. Repeat or descend.

This cheat sheet is optimized for digital reading and incident-time routing.

## 7) Fast routing bundles

Use these bundles when you need a first move in under 2 minutes.

- **Bundle A: overload + chaos**
  - First: `L0-C1` -> `L1-C4` -> `L3-C4`
  - Check: queue age, incident throughput, recovery window integrity.

- **Bundle B: green metrics, red reality**
  - First: `L3-C1` -> `L3-C6` -> `L5-C6`
  - Check: KPI/counter-KPI divergence, trace evidence consistency.

- **Bundle C: silent disengagement**
  - First: `L0-C2` -> `L2-C4` -> `L4-C2`
  - Check: participation authenticity and contradiction channel usage.

- **Bundle D: endless interpretation war**
  - First: `L3-C7` -> `L4-C7` -> (if unresolved) `L5-C7`
  - Check: axis-policy clarity and contradiction resolution lag.

## 8) Escalation guards

Escalate to depth mode immediately if any of these persist:

- any option yields same failure trajectory,
- readout cannot be trusted,
- contradiction channels are blocked by sanction risk,
- intervention effort rises while stabilization gain shrinks.

These are boundary-pressure indicators, not "communication problems".

