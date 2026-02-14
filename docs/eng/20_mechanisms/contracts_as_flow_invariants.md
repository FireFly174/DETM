# Contracts as transfer invariants (mechanism)

Status: mechanism (canonical at mechanism layer).

Note: first-pass translation of `docs/rus/20_mechanisms/contracts_as_flow_invariants.md`.

This card defines the external frame "levels / boundaries / contracts" and maps it to DETM
(`Ln`, `OuterFields`, subscriptions, and windows in base ticks).

Important:
- this is not API integration contract documentation;
- API/runtime integration format remains in `docs/eng/integration_contract.md`.

Related docs:
- boundary throughput and period scaling: `docs/eng/20_mechanisms/boundary_throughput_and_period_scaling.md`
- metrics/readout signals: `docs/eng/40_experiments/metrics.md`
- architecture and boundaries: `docs/eng/architecture.md`

---

## 1. Base assumptions (mechanism, not metaphysics)

1. A system exists operationally only if it has a boundary operator.
2. Externally relevant information is what survives transfer across that boundary.
3. Levels are not labels; they are modes defined by characteristic invariant-formation times.

In DETM:
- level boundary is represented by `OuterFields(Ln)` plus windowed formation rules;
- transfer survivors are published artifacts/readouts, not raw internal state.

---

## 2. Temporal localization of a level

Formulation:
- if response forms faster than neighboring-level invariant formation, signal and response remain same-level;
- if adjacent levels must be engaged, delays/search/waves appear.

Operationally:
- intra-level dynamics uses local topology at base ticks;
- cross-level dynamics uses publish/subscribe via boundary artifacts and windows.

Level remains distinguishable when there exists a window `T` where boundary readout correlation shape stays coherent under scaling.

---

## 3. No direct channels without boundaries

Intermediate levels may be skipped, but if two regimes interact, a boundary operator must exist:

```text
L3 -> boundary(L3-L1) -> L1
```

In DETM terms boundary is:
- aggregation operator;
- publication protocol.

Typical boundary parameters:
- memory window `T`;
- throughput (publish stride + channel bandwidth);
- effective delay;
- filters (what survives coarsening).

---

## 4. Intra-level vs cross-level dynamics

Inside a level, dominant modes are usually:
- local relaxation/diffusion/averaging;
- quasi-continuous behavior at small ticks.

Across levels, typical effects:
- transfer delay (window/stride);
- waves/oscillations;
- phase coupling/resonance when correlations survive;
- phase sensitivity when boundary readout keeps phase information.

Architectural consequence:
- top-down control is never instantaneous;
- cross-level influence is always mediated by memory and finite boundary bandwidth.

---

## 4.1 Cross-level control principle

Engineering form:

> Control degrades when direct cross-level channels bypass boundaries/institutions and feedback correction.

Problem is not technical impossibility of direct channel. Problem is loss of correction mechanisms:
- delay;
- aggregation;
- reconciliation;
- compensation.

In DETM any cross-level control must pass through bounded, windowed boundary operators.

---

## 5. What is above graph topology

Useful hierarchy:
- nodes -> states
- edges -> possible connections
- flows -> transfer over edges
- contracts -> stable flow invariants
- contract lifetimes -> stability horizon
- restructuring mechanisms -> search/waves/crises

Topology can remain while contract already died.

---

## 6. Contract definition in DETM

Definition:

> Contract is a stable transfer invariant between nodes or levels.

Contract is defined by transfer constraints, not static states:
- channel content;
- throughput per period;
- expectation envelope;
- memory window `T`;
- phase coherence condition;
- perturbation robustness.

Natural carriers in DETM:
- `OuterFields(Ln)` as impact/response alphabet;
- subscription spec as contract condition (channels, stride, window, filters).

---

## 7. Contract lifetime (`tau_contract`)

Definition:

> `tau_contract` is an interval where transfer invariant remains coherent and coordination cost stays bounded.

Operational proxies:
- stable boundary correlation time;
- narrowing boundary-flow spectrum with dominant peak;
- increasing phase-locking between regions/channels;
- no uncontrolled instability while throughput persists.

---

## 8. Meaning and selection

In this frame, "meaning" is not goal semantics.
It is a selection criterion for observables:
- survives boundary transfer;
- remains invariant under coarsening;
- preserves correlation under admissible window changes.

---

## 8.1 Architecturally unfair interactions

If there is an explicit boundary metric/detector, systems may optimize detector output instead of system stability.

This is a Goodhart-type failure:
- metric-targeting over contract-preserving control.

In this frame this is called architecturally unfair interaction.

---

## 9. Human-AI symbiosis as boundary operator

External framing in project terms:
- not "tool-user" relation;
- joint system with new higher-level boundary operator.

DETM mapping:
- human sets semantic policy (what is significant, windows/channels priorities);
- AI accelerates coarsening/search and helps stabilize selected invariants;
- symbiosis exists when a stable transfer contract forms between human signals and machine readout.

---

## 10. What to log for boundary/contract hypotheses

Aggregates only are insufficient for boundary fixed-point checks.

Minimum needed time series:
- `Phi_boundary(t)` throughput signal;
- `boundary_activity(t)` around pattern boundaries;
- phase/oscillator proxy (if defined);
- `div/curl` of flow when explicit flow exists.

Implementation note:
- can be reconstructed offline from stored fields;
- can also be emitted online as trace metrics.

