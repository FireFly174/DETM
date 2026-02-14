# Attractor influence radius and boundary throughput

Status: canonical mechanism card.

Note: first-pass translation of `docs/rus/20_mechanisms/attractor_influence_radius.md`.

This card introduces a formal notion of the attractor influence radius and a paired criterion based on boundary throughput.

It is used to:
- formalize system scale through boundaries (not volume);
- define system power/capacity as contour throughput;
- map "civilization type" style ideas into DETM language (throughput instead of source ownership).

---

## 1. Motivation

In DETM, the key quantity is not total volume but what flow can be:
- accepted;
- transformed;
- redistributed;
- dissipated;

while invariant structures remain stable.

This is naturally expressed via boundaries: flows are represented by a field `J`, and external interaction is represented through boundary contours.

---

## 2. Flow through a boundary

Given a flow field `J(r,t)`, define flow through a closed boundary `dOmega`:

- continuous form:

```text
Phi(dOmega, t) = integral_over(dOmega) J(r,t) * dS
```

- discrete lattice form:

```text
Phi(dOmega, t) = sum_{e in dOmega} J_e(t)
```

Sign convention:
- `Phi > 0`: net outflow;
- `Phi < 0`: net inflow.

---

## 3. Boundary throughput

Define boundary throughput as a time-averaged absolute flow:

```text
Throughput(dOmega) = < |Phi(dOmega, t)| >_t
```

This replaces "watts-like" interpretation:
- it does not depend on source type;
- it measures how much dynamics a system can pass through itself;
- it is directly related to stability and feedback.

---

## 4. Attractor influence radius

Let attractor `A` be localized in region `Omega0`.
Consider nested regions `Omega(R)` around its center.

Define influence radius `R_A` as the minimal `R` where external flow behavior is effectively compensated/saturated at attractor scale.

Equivalent operational conditions:

### 4.1 Throughput saturation

If:

```text
Throughput(dOmega(R)) -> const as R -> infinity
```

then `R_A` can be chosen where incremental change is small:

```text
|Throughput(R + dR) - Throughput(R)| < eps
```

### 4.2 Inflow/outflow balance

For a stable attractor:

```text
< Phi(dOmega(R_A), t) >_t ~= 0
```

Interpretation: no persistent net pumping across the selected boundary.

### 4.3 Compare against attractor "content"

If a measure `M_A` is defined (for example, integral of `E` over a region), choose `R_A` where:

```text
Throughput(dOmega(R_A)) ~ kappa * M_A
```

where `kappa` sets unit convention.

---

## 5. System type as throughput level

Working interpretation:

> System type is not "access to a source"; it is stable throughput through boundaries.

A type-X system can maintain and redistribute flows at scale X without destroying its own invariants.

---

## 6. Relation to DETM mechanisms

### 6.1 Subworld boundaries

Influence radius provides an operational way to choose active world boundaries:
- active world is defined by `dOmega(R)`;
- compute cost depends on boundary length and flow activity.

### 6.2 External links

Links implement boundary-crossing flow.
Throughput can be measured as:
- link contributions;
- plus internal flow on boundary edges.

### 6.3 Coarsener

The coarsener selects level/time scale so boundary throughput stays representable:
- flows too sharp/fast -> refinement;
- flows smooth/stable -> coarsen.

---

## 7. Practical experiment metric

For a selected attractor:
1. choose center `c`;
2. define `Omega(R)` family;
3. compute `Phi(dOmega(R), t)` per tick;
4. average to get `Throughput(R)`;
5. find `R_A` by saturation or balance criterion.

This yields two measurable characteristics:
- how far influence spreads;
- which flow level is sustained at the boundary.

---

## 8. Card invariants

1. Influence is measured as boundary flow.
2. Influence radius is defined over boundary families.
3. Throughput is the key system-type metric.
4. Boundaries are more informative than volume.
5. Mechanism is compatible with links/coarsener/refinement.

---

## 9. Purpose of this card

This card fixes the canonical method for defining scale via boundaries and flows in DETM.
