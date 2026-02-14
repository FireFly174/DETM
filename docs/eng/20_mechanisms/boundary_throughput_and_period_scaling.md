# Boundary throughput and period scaling (mechanism)

Status: mechanism (canonical at mechanism layer).

Note: first-pass translation of `docs/rus/20_mechanisms/boundary_throughput_and_period_scaling.md`.

In multi-level DETM, scaling should target transfer across boundaries, not raw fields.

Core object of renormalization:
- throughput through a boundary over a period.

Related docs:
- boundary as interface: `docs/eng/30_hypotheses/boundary_interface_holography.md`
- global tick and observation windows: `docs/eng/00_overview/architecture.md`
- outer fields and subscriptions: `docs/eng/architecture.md`
- contracts as transfer invariants: `docs/eng/20_mechanisms/contracts_as_flow_invariants.md`
- metrics and period classes: `docs/eng/40_experiments/metrics.md`

---

## 1. What is scaled (key shift)

In multi-level systems, "scale fields and expect self-similarity" is often not enough.
In DETM, scale the channel between regions/levels:

> renormalization target = boundary throughput per period.

Intuition:
- level `Ln` does not observe `Ln-1` internals directly;
- it observes what survives transfer through boundary readout on a window.

---

## 2. Boundary as phase-information carrier

Structural principle:

> A boundary carries phase/correlation structure only when the observation window is commensurate with the dynamics period.

In DETM terms:
- choose `window_ticks` commensurate with invariant `T_class`;
- otherwise phase is averaged out and only coarse aggregates remain.

---

## 3. Boundary throughput functional

For an object/region `M` and boundary `dM`, define:

```text
F_boundary(T) = integral_{t..t+T} Phi_boundary(tau) dtau
```

Where:
- `T`: window length in base ticks;
- `Phi_boundary`: boundary flow proxy (energetic/causal).

In early versions, `Phi_boundary` may be proxy-based (gradients/lag/flow estimates), but it must remain observable and reproducible.

---

## 4. Cross-level scaling via `F_boundary(T)`

For transition `Ln-1 -> Ln`, find regimes where boundary response shape is retained while period scales:
- `T -> alpha * T`;
- `F_boundary(T)` changes coherently (for example, `F(alpha*T) ~= alpha^k * F(T)`);
- invariant remains in the same class (`T_class` and identity stable).

This is scaling transfer, not scaling fields.

---

## 5. Practical proxies for `Phi_boundary`

If explicit flow field `J` is unavailable, use:
- boundary `|grad(E)|` as interface activity indicator;
- lag-correlation across opposite sides of boundary (`exp_transfer_speed.md`);
- region energy delta over window (corrected for external source/sink if present);
- outer/readout channels (`boundary_activity`, `strength`) as compiled boundary observables.

---

## 6. Relation to outer fields

`OuterFields` should carry what reaches the next level after window-based aggregation.

Practical baseline:
- interpret `boundary_activity` and `strength` as windowed proxies of `Phi_boundary`;
- optionally add derived channel `throughput_per_period` over `window_ticks`.

