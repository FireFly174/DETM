# DETM Book (EN v2 quick) [draft]

_mode: draft_

## Содержание

1. Where to start (short hook)
2. Levels map (L0..L5)
3. Quickstart (10 minutes)
4. First aid protocol (when the system is melting)
5. Reader map
6. How to read this book
7. Level summaries (one-page)
8. Navigation cheat sheet (S-T-C)
9. Invariants and tests
10. Terms
11. Index (keywords)
12. Case registry (compact)

## Where to start (short hook)

Imagine a bridge.

From outside it looks fine: traffic moves, reports are green, dashboard numbers grow.
But inside, the bridge stands only because load, joints, corrosion, maintenance, and tolerance are still under control.

Complex human systems break in the same way:
- language keeps working while causality is already broken,
- metrics keep growing while reality degrades,
- institutions protect capture rather than stability,
- the regime crosses a boundary and old optimization no longer converges.

This book is not a moral manifesto.
It is a diagnostic framework:
1. locate the failing level,
2. restore causality with a minimal operator,
3. move back from emergency to controlled adaptation.

Core idea:

> Most system conflicts are level-mismatch conflicts.

One actor talks about basis (L0), another about actions (L1), another about narratives (L2), another about rules (L3), and another about institutional power (L4/L5).

## Levels map (L0..L5)

The model uses six operational levels.

| Level | Question | Typical failure | Typical operator |
|---|---|---|---|
| L0 | Does the system still hold? | basis collapse, fake participation | stop, exit, load reduction |
| L1 | Do actions produce verified effects? | activity without effect | minimal action + readout |
| L2 | Which stories/roles gate behavior? | rationalization, taboo, shame loops | reframe + permission update |
| L3 | Which metrics/rules define reality? | Goodhart, metric theater | axis policy, anti-capture checks |
| L4 | Who can change rules legitimately? | institutional capture | governance reset, veto rights |
| L5 | Where are the regime boundaries? | delayed transition, hard crash | transition protocol |

Use this map as routing logic, not ideology.

## Quickstart (10 minutes)

<a id="quickstart"></a>

### 1) One-sentence summary

Systems tend to optimize what is cheapest to hold now, and fail where regime-holding cost stops converging.

### 2) 60-second model map

- L0: basis/existence (0/1)
- L1: action -> observable effect
- L2: narratives and role contracts
- L3: metrics/rules/axis policy
- L4: institutions and sanctioning power
- L5: boundaries and transitions

### 3) First move protocol

If "any option leads to the same failure": go depth-first (L3 -> L1 -> L0).
If causality holds but choice is unclear: go breadth-first (usually L2/L3).

### 4) Starter symptoms

- Fires everywhere, overload: start `L0-C1` (pause/stop)
- Metrics up, reality down: start `L3-C6` (break metric game)
- No clear next step: start `L1-C2` (minimal readout)
- Narrative deadlock: start `L3-C7` (axis policy)

### 5) Fast navigation

Use `Sx/Ty` and `Lx-Cn` codes from appendix navigation to jump directly to the needed operator.

## First aid protocol (when the system is melting)

Use this in emergency mode before deep analysis.

1. Freeze escalation (`L0-C1`): stop adding commitments.
2. Restore a truthful sensor (`L0-C6`/`L1-C2`): one observable that cannot be faked cheaply.
3. Remove impossible scope (`L0-C4`): reduce obligations to sustainable capacity.
4. Isolate toxic coupling (`L0-C5`): quarantine the failure amplifier.
5. Decide path:
   - if causality returns -> move to L1/L2 refinement,
   - if causality does not return -> execute transition logic (L5).

Rule:

> In emergency, survival of causality has priority over optimization of goals.

## Reader map

Choose your route.

### Practitioner route

`Quickstart -> L0 -> L1 -> L3 -> L5 -> Appendix: Navigation`

Use this route if you need immediate operational decisions.

### Research route

`Thesis -> L0..L5 -> Invariants and tests -> Case registry`

Use this route for model building and hypothesis design.

### Governance route

`L3 -> L4 -> L5 -> Case registry`

Use this route for institutional design, policy and anti-capture work.

## How to read this book

This is a diagnostic and operator handbook.

Reading rules:
1. Start from observed symptoms, not from favorite theory.
2. Identify active level(s) first.
3. Apply one operator at a time.
4. Validate with readout panel (never one KPI).
5. Escalate to deeper level only if current level does not restore causality.

Terminology:
- `Sx/Ty`: scene/topic code (where the symptom appears)
- `Lx-Cn`: level/operator code (what to do next)

For implementation links, use:
- `docs/eng/*` for narrative
- `docs/rus/ROADMAP.md` for execution status
- runtime tests/artifacts for verification.

## Level summaries (one-page)

- **L0**: existence/basis. If L0 breaks, all upper optimization is noise.
- **L1**: minimal action-effect loop. No readout, no control.
- **L2**: narratives and role contracts that allow or block action.
- **L3**: metric/rule layer. Main Goodhart risk zone.
- **L4**: institutional authority and legitimacy.
- **L5**: boundaries, transitions, and irreversible regime shifts.

Quick routing:
- collapse symptoms -> L0 first,
- fake progress symptoms -> L3 first,
- confusion/no-step symptoms -> L1 first,
- authority conflict symptoms -> L4/L5.

## Navigation cheat sheet (S-T-C)

<a id="nav-cheatsheet"></a>

### Scenes

- `S1`: person
- `S2`: family/close network
- `S3`: society/game layer
- `S4`: organization
- `S5`: state/institutions

### Topics

- `T1`: pause/stop
- `T2`: refusal/exit
- `T3`: heroic overuse
- `T4`: obligation reduction
- `T5`: quarantine
- `T6`: feedback restoration
- `T7`: interpretation/axis control

### Operator map

- L0: `L0-C1..C7` (existence operators)
- L1: `L1-C1..C7` (action/readout operators)
- L2: `L2-C1..C7` (narrative/role operators)
- L3: `L3-C1..C7` (metric/rule operators)

Search tips:
- combine scene + topic (`S4/T6`),
- or jump directly by operator code (`L3-C7`).

## Invariants and tests

This checklist aligns book-level diagnostics with repo-level verification.

### Invariants

1. Causality can be measured (no blind optimization).
2. Readout is multi-signal (anti-Goodhart).
3. Basis stress is visible before collapse.
4. Rule changes preserve rollback path.
5. Transition criteria are explicit before regime switch.

### Practical tests

- reproducible headless runs (`catalog/metrics/summary/final_state`),
- trace/watch linkage (`trace_ref` continuity),
- metric-countermetric consistency,
- no hidden dependency from core (`detm/*`) to app UI.

For current execution status, see `docs/rus/ROADMAP.md`.

## Terms

- **Basis (L0)**: minimal contracts/resources that keep causality alive.
- **Readout**: multi-signal observation panel used for decision validation.
- **Goodhart mode**: optimization of a sensor that degrades real dynamics.
- **Axis policy**: explicit choice of which projections/metrics define reality.
- **Capture**: concentration of interpretation/rule power in one actor/group.
- **Transition**: explicit regime shift when current mode no longer converges.
- **Invariant**: retained class/property under perturbation.
- **Operator**: minimal action that changes state in a verifiable way.

## Index (keywords)

- anti-capture
- anti-goodhart
- axis policy
- basis / L0
- boundary / transition
- causality
- default rate
- invariant
- metric theater
- operator
- readout panel
- regime change
- rollback
- scope reduction
- transition protocol

## Case registry (compact)

<a id="case-registry"></a>

Use this table as an entry point.

| Symptom | First code | Typical follow-up |
|---|---|---|
| overload, fire mode | `L0-C1` | `L0-C4`, `L1-C2` |
| fake progress | `L3-C6` | `L3-C7`, `L1-C2` |
| no next step | `L1-C2` | `L1-C1`, `L2-C7` |
| role conflict | `L2-C5` | `L3-C7`, `L4` checks |
| capture suspicion | `L4` audit | `L3-C7`, `L5` transition criteria |

Extend this registry with domain-specific scenarios.

---

_stats: chars=8049, words=1138, pages=4.5 (rough)_
