# DETM Book (EN v2) [draft]

_mode: draft_

## Содержание

1. Where to start (short hook)
2. Levels map (L0..L5)
3. Quickstart (10 minutes)
4. First aid protocol (when the system is melting)
5. Thesis
6. Reader map
7. How to read this book
8. L0: Existence (0/1) as minimal invariant
9. 01_L1
10. 01_L2
11. 01_L3
12. 01_L4
13. 01_L5
14. Terms
15. Case registry (compact)
16. Navigation cheat sheet (S-T-C)
17. Invariants and tests
18. Index (keywords)

## Where to start (short hook)

Imagine a bridge.

From the outside, everything looks healthy: traffic flows, dashboards are green, reports look convincing.
But bridges do not stand on reports. They stand on load limits, joints, maintenance windows, and the honesty of stress signals.

Human systems fail the same way.
Usually not because nobody "wants good results", but because the system quietly learns that imitation is cheaper than reality:

- language still sounds correct while causality is already broken,
- metrics keep improving while field outcomes degrade,
- institutions defend capture instead of resilience,
- the old regime passes its boundary and no longer converges.

This book is not a moral lecture and not a motivational script.
It is an operational diagnostic guide:

1. identify the active failure level,
2. apply the smallest operator that restores causality,
3. move from emergency stabilization to controlled adaptation.

Core claim:

> Most hard system conflicts are conflicts between levels of description.

One actor speaks L0 (basis), another speaks L1 (actions), another speaks L2 (stories), another speaks L3 (metrics and rules), and another speaks L4/L5 (institutions and boundaries).
They can all be "right" locally and still produce collective failure globally.

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

## Thesis

This book is about how systems hold a regime, and at what price.

By "system" we mean any coordinated structure where action and consequence must stay linked:
person, family, team, organization, institution, state.
By "regime" we mean the currently active way of operating: action cadence, feedback quality, cost distribution, and boundary handling.

The practical thesis is strict:

1. Stability is not produced by good intentions. It is produced by convergent basis contracts.
2. Learning is not "loss goes down". Learning is invariant retention under perturbation.
3. Metrics are sensors, not truth.
4. Rules are cost architecture, not morality.
5. Institutional quality is anti-capture plus reversibility.
6. Boundary crossing without transition protocol creates systemic debt.

Another way to read it:

- if report quality is decoupled from pain/cost, systems train reward hacking;
- if stopping rights are taboo, error debt accumulates invisibly;
- if axis policy is implicit, metric wars replace control.

Pragmatic consequence:

- diagnose by level (`L0..L5`),
- act with the smallest operator that restores causality,
- validate by multi-signal readout, never by one KPI.

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

## L0: Existence (0/1) as minimal invariant

L0 is the basis layer.
It does not ask whether the system is efficient, elegant, or successful.
It asks a harder question:

> Can this system still keep action and consequence connected over the current horizon?

Operationally:

- `L0 = 1`: basis contracts still hold (with recoverable default rate).
- `L0 = 0`: basis defaults are systemic and causality degrades into noise.

### Why L0 matters

When L0 collapses, upper layers become decorative:

- L1 becomes activity theater,
- L2 becomes rationalization,
- L3 becomes metric gaming,
- L4 becomes enforcement of drift,
- L5 arrives as forced transition instead of planned transition.

### Typical L0 signals

- recurrent default on basic promises,
- imitation replacing real participation,
- chronic overload with no recovery windows,
- silent withdrawal from key actors,
- rising effort for shrinking stabilizing effect.

### Core operators

- `L0-C1`: pause/stop to prevent nonlinear escalation,
- `L0-C2`: refusal/exit as truthful diagnostic signal,
- `L0-C4`: obligation reduction to sustainable capacity,
- `L0-C5`: quarantine of toxic coupling,
- `L0-C6`: restoration of feedback that cannot be faked cheaply.

### Readout panel

- basis stability rate,
- basic-default frequency,
- participation authenticity,
- recovery-window integrity,
- intervention-energy / stabilization-gain ratio.

If L0 cannot be restored in bounded attempts, switch from optimization mode to L5 transition mode.

## 01_L1

﻿# L1: Minimal operation and verified effect (v2 draft)

### 1) Operational role of L1

L1 is the action-effect layer.
It answers one practical question:

> Which minimal action produces a verifiable state change within the current horizon?

L1 is where many systems first *look* productive while becoming less controllable.
You can be very active and still lose causality.

#### L0 dependency: L1 cannot be stable without basis

If basis (`L0`) is depleted, L1 quickly degrades into:
- emergency triage,
- random urgency,
- fake completion,
- delayed hidden debt.

So L1 is never independent. It is an execution lens constrained by L0.

#### How L0 themes `T1..T7` surface on L1

- `T1` pause/stop: action pipeline is interrupted to prevent further drift.
- `T2` refusal/exit: participation drops, silent queue growth appears.
- `T3` heroic mode: temporary throughput spike with long-term collapse risk.
- `T4` obligation reduction: visible scope contraction and clearer completion rules.
- `T5` quarantine: selective isolation of unstable paths.
- `T6` feedback restoration: shorter loops and better incident visibility.
- `T7` axis control conflict: teams debate KPI semantics instead of shipping verified effect.

#### L1 as leverage

L1 is the fastest place to restore local control:
- shrink cycle,
- define one truthful readout,
- stop parallel overload,
- recover "done = verified" semantics.

#### L1 as a risk zone

Without guardrails, L1 becomes a stress amplifier:
- speed increases while reliability drops,
- incident handling becomes blame handling,
- teams optimize closure artifacts instead of field effects.

#### Applicability limits

L1 operators are not enough when:
- basis is structurally broken (L0 issue),
- metric policy is captured (L3 issue),
- transition boundary is crossed (L5 issue).

---

### 2) Typical L1 regimes

#### Psychology / individual

**Reactive loop mode**:
- person executes nearest task,
- horizon collapses to "today",
- no energy for model update.

**Perfection trap mode**:
- action starts only with complete certainty,
- cycle time explodes,
- no learning from fast probes.

#### Team / organization

**Queue pressure mode**:
- too much work-in-progress,
- ownership diffuses,
- latency dominates quality.

**Heroic patch mode**:
- visible short-term wins,
- invisible maintenance debt,
- fragile recovery capacity.

#### System / governance

**Metric-delivery mismatch mode**:
- reports close faster than defects,
- problem age grows,
- escalation becomes normal workflow.

---

### 3) Cross situations: operators at L1

#### L1-C1: Minimum viable action instead of "solve everything"

Define the smallest action that can change the state.
No multi-goal bundles.

#### L1-C2: Minimum truthful readout

One sensor that cannot be cheaply faked.
Readout is not performance theater; it is control evidence.

#### L1-C3: Shorten cycle length

Prefer more frequent, lower-complexity loops over long opaque cycles.

#### L1-C4: Reduce parallelism

Stop uncontrolled intake.
Preserve completion flow before increasing throughput.

#### L1-C5: Incident review without punishment bias

Treat incident as a signal about operator quality,
not as a hunt for a symbolic culprit.

#### L1-C6: Recovery windows as part of execution contract

Include maintenance/recovery in the plan.
No recovery -> fake capacity.

#### L1-C7: "Done = verified"

A task is done only if effect is observed,
not when status field is closed.

---

### 4) Cross-level effects: how L1 behaves under upper-level pressure

#### L1 under L2 pressure

If narratives forbid bad news, L1 readout quality collapses.
Execution speed may look high, but learning speed goes to zero.

#### L1 under L3 pressure

When KPI is treated as goal, L1 adapts to gaming surfaces.
You get faster reporting, not better dynamics.

#### L1 under L4 pressure

If governance blocks pause rights, L1 cannot de-risk escalation.
Then "execution" becomes forced drift.

#### L1 under L5 pressure

Near boundary, local optimization stops converging.
L1 operators must switch from throughput logic to transition support logic.

---

### 5) Diagnostics (`try/except`): where L1 fails in real systems

#### Typical errors

- high task closure with no field improvement,
- chronic urgent queue,
- repeated incidents with no operator update,
- completion semantics detached from verification.

#### Typical fixes

- enforce `L1-C2` before adding new KPIs,
- cap WIP (`L1-C4`),
- bind completion to observed effect (`L1-C7`),
- add explicit recovery slots (`L1-C6`).

---

### One-minute summary

L1 is where systems either recover control or institutionalize imitation.
If action-effect linkage is not explicit and measured, speed is not progress.

## 01_L2

﻿# L2: Narratives, roles, and interpretation (v2 draft)

### 1) Operational role of L2

L2 is the semantics layer.
It defines which explanations, roles, and identity contracts are considered legitimate.

Practical question:

> Which narratives enable truthful action, and which narratives block it?

L2 matters because people do not execute raw logic.
They execute logic filtered through role permission, fear, status, and meaning.

#### L0 dependency

When basis is unstable, L2 often shifts into defensive storytelling:
- denial,
- blame simplification,
- hero mythology,
- taboo on pause/exit.

This is not "bad culture" by default; it is often compensation for basis stress.

#### How `T1..T7` surface in L2

- `T1` pause: framed as responsibility or framed as betrayal.
- `T2` refusal: framed as signal or framed as disloyalty.
- `T3` heroism: framed as virtue, even when it burns capacity.
- `T4` reduction: framed as realism or framed as weakness.
- `T5` quarantine: framed as protection or as political punishment.
- `T6` feedback: framed as learning or as threat.
- `T7` axis control: framed as "objective truth" while hiding choice of projection.

#### L2 as leverage

L2 can re-open blocked action without changing hard infrastructure:
- permission to report bad news,
- permission to stop,
- permission to run small experiments.

#### L2 as risk zone

If L2 is captured, every lower-level operator is distorted:
- L1 becomes symbolic busyness,
- L3 becomes rhetorical KPI policy,
- L4 legitimizes capture.

#### Applicability limits

L2 reframing does not fix:
- hard basis collapse (L0),
- structurally toxic incentive architecture (L3),
- failed transition boundaries (L5).

---

### 2) Typical L2 regimes

#### Psychology / individual

**Shame-gated action**:
- people avoid truthful readout to avoid identity loss.

**Narrative overfitting**:
- one explanatory frame applied to all failures,
- no model update under new evidence.

#### Team / organization

**Blame theater**:
- symbolic culprit assignment replaces operator redesign.

**Heroic identity lock**:
- exhaustion becomes proof of loyalty.

#### System / governance

**Official-story monopoly**:
- contradictory observations are delegitimized,
- model diversity collapses,
- control quality decays.

---

### 3) Cross situations: operators at L2

#### L2-C1: Replace blame loop with causal diagnosis

Move from "who is guilty" to "which operator failed".

#### L2-C2: De-normalize heroic overuse as a baseline

Treat hero mode as emergency exception, not identity norm.

#### L2-C3: Remove taboo on stopping

Pause must be an allowed stability operator.

#### L2-C4: Normalize refusal as a diagnostic signal

Refusal is often a high-value early warning of non-convergent cost.

#### L2-C5: Reframe what counts as reality

Explicitly switch from prestige narratives to observable dynamics.

#### L2-C6: Remove taboo on inconvenient observations

If bad news is unsafe, the system cannot learn.

#### L2-C7: Replace explanation-only mode with experiment-first mode

No narrative is valid without readout-backed perturbation testing.

---

### 4) Cross-level effects

#### L2 under L1 pressure

When execution pressure is extreme, L2 simplifies into tactical slogans.
This increases speed but reduces model precision.

#### L2 under L3 pressure

Metric regime defines which stories survive.
Captured metrics create captured narratives.

#### L2 under L4 pressure

Institutional sanctioning decides whether truth-speaking roles can exist.

#### L2 under L5 pressure

During transition, old identity contracts can become non-viable.
L2 must update legitimacy grammar for the new regime.

---

### 5) Diagnostics (`try/except`)

#### Typical errors

- "We explained everything" but no improvement in field behavior,
- stopping framed as disloyalty,
- recurring taboo around incident evidence,
- story consistency prioritized over causal validity.

#### Typical fixes

- enforce `L2-C7`: explanation requires a test path,
- protect bad-news channels (`L2-C6`),
- remove moral framing from pause/exit operators (`L2-C3`, `L2-C4`),
- connect L2 narratives to L1/L3 readout.

---

### One-minute summary

L2 decides whether truth is operationally legal.
If role grammar punishes reality contact, no technical fix will scale.

## 01_L3

﻿# L3: Metrics, rules, and axis policy (v2 draft)

### 1) Operational role of L3

L3 is the policy layer that defines what the system accepts as measurable reality.

Practical question:

> Which projections are used for decision-making, and how is their validity controlled?

L3 is powerful because it shapes incentives, attention, and accountability.
It is dangerous because it can optimize report quality while degrading field dynamics.

#### L0 dependency

When basis stress grows, L3 often drifts toward report-preserving policy:
- cost is pushed downward,
- risk is hidden in lagging indicators,
- contradiction is normalized as temporary noise.

#### How `T1..T7` surface in L3

- `T1` stop-right appears as formal stop-rules or is removed from policy.
- `T2` refusal appears as attrition/withdrawal data, or gets hidden.
- `T3` hero mode appears as incentive structure rewarding overuse.
- `T4` reduction appears as controlled scope renegotiation.
- `T5` quarantine appears as containment policy boundaries.
- `T6` feedback appears as protected negative-signal channels.
- `T7` axis control appears as explicit or hidden metric governance.

#### KPI: sensor vs objective

At L3, the key distinction is binary:
- sensor mode: metric helps detect dynamic state,
- objective mode: metric becomes target and invites gaming.

Most Goodhart failures are objective-mode failures.

#### L3 as leverage

- define axis policy explicitly,
- require counter-signals for every target metric,
- tie rule changes to rollback procedures,
- return error cost to source.

#### L3 as risk zone

- dashboard theater,
- metric-induced capture,
- growth of commitments detached from capacity.

#### Applicability limits

L3 cannot substitute for:
- missing basis (`L0`),
- broken action-readout loop (`L1`),
- absent institutional legitimacy (`L4`).

---

### 2) Typical L3 regimes

#### Psychology / individual

**Self-scoring trap**:
- person optimizes visible score,
- invisible debt accumulates.

#### Team / organization

**KPI monoculture**:
- one dominant metric suppresses contradiction,
- local teams learn report optimization.

#### System / governance

**Axis monopoly**:
- one authority controls which indicators are "real",
- policy criticism is reframed as disloyalty.

---

### 3) Cross situations: operators at L3

#### L3-C1: Metric as readout, not final objective

Define what the metric observes and what it does not observe.

#### L3-C2: Remove incentives that grow heroic overuse

Do not reward chronic emergency mode as baseline performance.

#### L3-C3: Renegotiate obligations to real capacity

Policy that ignores capacity eventually destroys policy credibility.

#### L3-C4: Stop-rule guardrails

Formal criteria to freeze escalation before non-linear failure.

#### L3-C5: Return error cost to source

No hidden cost transfer to downstream actors.

#### L3-C6: Break report theater

Require trace-level evidence for major claims.

#### L3-C7: Explicit axis policy

Make projection choice auditable:
- who chooses axes,
- why,
- with which counter-signals,
- under what rollback conditions.

---

### 4) Cross-level effects

#### L3 under L1 pressure

Execution urgency can promote simplistic metric policy.
If uncorrected, this produces fast local closure and slow global collapse.

#### L3 under L2 pressure

Narratives determine which metric contradictions are socially acceptable.
L2 capture tends to precede L3 capture.

#### L3 under L4 pressure

Without institutional anti-capture, axis policy centralizes power.
Then metric debate becomes governance conflict.

#### L3 under L5 pressure

Near regime boundary, old metrics lose explanatory power.
L3 must support transition readout redesign.

---

### 5) Diagnostics (`try/except`)

#### Typical errors

- rising KPI with declining field reliability,
- absence of independent counter-signals,
- retrospective metric redefinition,
- policy updates without rollback path.

#### Typical fixes

- enforce metric + counter-metric pairs,
- publish axis policy (`L3-C7`),
- link policy claims to trace artifacts,
- couple rule deployment with rollback tests.

---

### One-minute summary

L3 is where systems choose between control and theater.
If metrics define reality without validity constraints, the system trains deception as a rational strategy.

## 01_L4

﻿# L4: Institutions, power, and anti-capture (v2 draft)

### 1) Operational role of L4

L4 is the institutional layer.
It defines who can change rules, who can block harmful decisions, and how legitimacy is maintained.

Practical question:

> Can the system correct itself without depending on heroics or personal luck?

If L4 is weak, even good L1/L3 operators degrade over time.

#### L0 dependency

Institutional quality is constrained by basis realism.
When basis stress is denied, institutions drift toward symbolic enforcement.

#### How `T1..T7` surface in L4

- `T1` pause: is stop-right institutionalized or punished?
- `T2` refusal: is exit protected or criminalized by policy?
- `T3` heroism: does governance rely on chronic overuse?
- `T4` reduction: can obligations be legally resized to capacity?
- `T5` quarantine: can toxic loops be isolated by protocol?
- `T6` feedback: are truthful signals institutionally protected?
- `T7` axis control: who has authority to define system reality?

#### L4 as leverage

- distribute veto and stop rights,
- define rollback procedures,
- separate audit from political loyalty,
- keep interpretation power plural.

#### L4 as risk zone

- concentrated interpretation monopoly,
- no reversible path for failed policies,
- symbolic governance replacing operational governance.

#### Applicability limits

L4 changes are slower than L1/L2 interventions.
Use L4 as stability architecture, not as instant firefighting.

---

### 2) Typical L4 regimes

#### Psychology / individual institutions

**Founder capture mode**:
- one interpretation center,
- dissent reframed as betrayal.

#### Team / organization

**Policy theater mode**:
- formal controls exist,
- but enforcement follows informal power.

#### System / state

**Legitimacy drift mode**:
- decisions remain legal but lose perceived fairness,
- compliance drops,
- hidden opposition grows.

---

### 3) Cross situations: operators at L4

#### L4-C1: Institutionalize stop/veto rights

Without stop-rights, escalation has no brake.

#### L4-C2: Protect truthful feedback channels

Feedback cannot depend on individual courage alone.

#### L4-C3: De-incentivize structural hero mode

Institution must not reward chronic overuse as normal behavior.

#### L4-C4: Enable obligation renegotiation by protocol

Capacity mismatch must be resolvable institutionally, not privately.

#### L4-C5: Quarantine protocol for toxic loops

Contain instability before it propagates across the whole system.

#### L4-C6: Reversibility by design

Every high-impact rule change requires rollback pathway.

#### L4-C7: Transparent axis-governance process

Make metric/axis control a formal, auditable process.

---

### 4) Cross-level effects

#### L4 under L1 pressure

Operational urgency can bypass governance.
If this becomes standard, institutions become decorative.

#### L4 under L2 pressure

Narrative capture often precedes institutional capture.
Role grammar shapes who is seen as legitimate.

#### L4 under L3 pressure

Metric policy can centralize power silently.
Axis control is governance control.

#### L4 under L5 pressure

Boundary transitions require institutional transitions.
Old legitimacy schemes may not survive regime change.

---

### 5) Diagnostics (`try/except`)

#### Typical errors

- no practical mechanism to stop harmful trajectories,
- governance decisions that cannot be rolled back,
- audit channels subordinated to political loyalty,
- legitimacy claims unsupported by repair capacity.

#### Typical fixes

- codify veto/stop rights (`L4-C1`),
- enforce rollback before deployment (`L4-C6`),
- protect independent feedback channels (`L4-C2`),
- externalize axis-policy decisions with traceability (`L4-C7`).

---

### One-minute summary

L4 decides whether correction is institutional or accidental.
No anti-capture architecture -> no long-horizon controllability.

## 01_L5

﻿# L5: Boundaries and regime transitions (v2 draft)

### 1) Operational role of L5

L5 is the boundary layer.
It handles situations where the current mode of optimization stops converging.

Practical question:

> Are we still in a tunable regime, or already in a regime that must be changed?

L5 is not a "higher abstraction for discussion".
It is where delayed transition becomes structural damage.

#### L0 dependency

L5 cannot be interpreted correctly without basis signals.
If basis stress is hidden, transition is usually delayed until forced collapse.

#### How `T1..T7` surface in L5

- `T1` pause becomes transition precondition,
- `T2` refusal becomes boundary evidence,
- `T3` heroism becomes transition postponement cost,
- `T4` reduction becomes pre-transition stabilization,
- `T5` quarantine becomes boundary containment,
- `T6` feedback restoration becomes transition navigation instrument,
- `T7` axis control conflict becomes regime-legitimacy conflict.

#### L5 as leverage

- define explicit transition triggers,
- separate tuning problems from regime problems,
- preserve reversibility where possible,
- limit irreversible debt during switch.

#### L5 as risk zone

- transition denial,
- endless local patching after global non-convergence,
- irreversible commitments before transition criteria are met.

#### Applicability limits

L5 is expensive and disruptive.
Do not use transition logic for ordinary L1/L3 tuning problems.

---

### 2) What changes from L0 to L5

Across levels, the system shifts from local correction to regime selection.

- L0: existence and basis integrity,
- L1: action/readout control,
- L2: narrative and role legitimacy,
- L3: metric/rule architecture,
- L4: institutional correction capacity,
- L5: boundary crossing and regime replacement.

At L5, old success metrics may become misleading.
The primary objective is safe regime switch, not local KPI growth.

---

### 3) Cross situations: operators at L5

#### L5-C1: Transition trigger criteria

Define conditions that force transition mode.
No trigger policy -> endless denial loop.

#### L5-C2: Bound mode by horizon and debt budget

Transition must be constrained by explicit limits.

#### L5-C3: Classify boundary type

Distinguish local overload from structural non-convergence.

#### L5-C4: Controlled shutdown / controlled contraction

Prefer bounded contraction over chaotic collapse.

#### L5-C5: Contract renegotiation before restart

Do not relaunch old commitments on new capacity reality.

#### L5-C6: Post-transition readout reset

Use new readout panel aligned with new regime dynamics.

#### L5-C7: Exit path from transition mode

Transition without exit criteria becomes permanent emergency.

---

### 4) Cross-level effects

#### L5 under L1 pressure

Execution teams may keep patching even when transition is needed.
This hides boundary evidence.

#### L5 under L2 pressure

Identity narratives can block transition acknowledgement.
"We are not the type of system that stops" is a common failure phrase.

#### L5 under L4 pressure

Institutional rigidity can convert manageable transition into hard breakdown.

#### L5 under L5 pressure

Nested transitions may appear when the first transition is under-scoped.
Use staged boundaries, not one giant irreversible jump.

---

### 5) Diagnostics (`try/except`)

#### Typical errors

- repeated stabilization attempts with shrinking effect,
- intervention energy rises while controllability falls,
- persistent mismatch between report and trace,
- no formal transition trigger despite obvious boundary signs.

#### Typical fixes

- define `L5-C1` trigger policy,
- cap intervention debt (`L5-C2`),
- perform boundary classification (`L5-C3`),
- execute controlled contraction (`L5-C4`),
- reset contracts and readout (`L5-C5`, `L5-C6`).

---

### One-minute summary

L5 is where systems choose between planned transition and unplanned collapse.
If regime non-convergence is treated as a local tuning issue, failure becomes structural.

## Terms

- **Basis (L0)**: minimal contracts/resources that keep causality alive.
- **Readout**: multi-signal observation panel used for decision validation.
- **Goodhart mode**: optimization of a sensor that degrades real dynamics.
- **Axis policy**: explicit choice of which projections/metrics define reality.
- **Capture**: concentration of interpretation/rule power in one actor/group.
- **Transition**: explicit regime shift when current mode no longer converges.
- **Invariant**: retained class/property under perturbation.
- **Operator**: minimal action that changes state in a verifiable way.

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

---

_stats: chars=31833, words=4372, pages=17.7 (rough)_
