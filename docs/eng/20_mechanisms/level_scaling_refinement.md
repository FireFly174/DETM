# Level Scaling and Mandatory Refinement

## Status
Canonical mechanism specification.

This document defines the strict invariants and mechanisms governing
level representation, scaling, and refinement in DETM.

---

## 1. Energy as a Representational Invariant

In DETM, energy is normalized:

E ∈ [0;1]

This is not a heuristic threshold and not a physical bound.
It is a strict limit of representability at a given level.

Any state violating this invariant cannot be correctly represented
at the current level.

---

## 2. Linear Coupling of Space and Time

DETM enforces linear scaling:

- scaling spatial resolution by factor k
- requires scaling temporal resolution by factor k

Formally:

(x, t, E) → (k·x, k·t, E)

Levels differ only by representational scale, not by dynamics.

---

## 3. Levels as Forms of Representation

A level Ln is not a separate physical system.
It is a form of representation with a fixed resolution.

One cell of Ln+1 corresponds to a region of Ln.

Transitions between levels are representational transforms:
- coarsen: Ln → Ln+1
- refine:  Ln+1 → Ln

---

## 4. Loss of Mantissa as Legitimate Reduction

Contributions far below the active scale of a level
are indistinguishable and may be discarded.

This allows reductions such as:

float (Ln) → boolean (Ln−1)

This is not information loss, but a reduction of distinguishability.

---

## 5. Meaning of E > 1

E > 1 does not indicate physical excess.
It indicates representational overflow.

The current level is no longer sufficient to encode the state.

This condition mandates refinement.

---

## 6. Mandatory Local Refinement

Refinement is not optional and not heuristic.

Algorithmically:

1. Compute step at level Ln
2. Detect regions where E > 1
3. For each connected region:
   - refine to Ln−1
   - evolve until E ≤ 1
   - coarsen back to Ln
4. Continue computation at Ln

Refinement is:
- local
- deterministic
- invariant-preserving

---

## 7. Coarsen / Refine Are Not Backpropagation

Despite naming similarity, these operations are not gradient-based.

They are scale transforms:
- no loss history required
- no optimization objective
- no learning

They exist solely to preserve representability.

---

## 8. GPU-Oriented Interpretation

Representation must use dense tensor fields.
Per-cell object pointers are forbidden.

Refinement operates on connected regions via masks,
not on individual cells.

---

## 9. Summary of Invariants

- E ∈ [0;1] is mandatory
- Space and time scale linearly
- Levels differ only by representation
- E > 1 forces refinement
- Reduction of mantissa is legitimate
- Refinement is local and reversible (w.r.t invariants)

---

This mechanism is foundational.
All implementations must preserve these invariants.
