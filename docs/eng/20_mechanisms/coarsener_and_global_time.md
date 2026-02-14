# Coarsener and global time

## Status

Canonical mechanism specification.

Note: first-pass translation of `docs/rus/20_mechanisms/coarsener_and_global_time.md`.

This card fixes the coarsener role as time-scale controller in DETM.

The coarsener is:
- not a classical task scheduler;
- not a physical-clock manager.

It selects representation level and interprets time in global ticks.

---

## 1. Two times in the system

### 1.1 Execution time

- wall-clock runtime on CPU/GPU/IO;
- measured in seconds;
- environment-dependent;
- not canonical model time.

### 1.2 Global time

- logical model time;
- measured in ticks (`global tick`);
- defines ordering and duration in model terms.

The coarsener maps between these notions but never conflates them.

---

## 2. L0 global tick and run base tick

Canonical global tick (`GlobalTick(L0)`) is one step at level `L0`.

A run may choose `base_level = Lmin` and count time in `BaseTick(Lmin)`.
This is a simulation boundary choice, not an alternative time ontology.

Properties:
- each global tick maps to one L0 step;
- execution-time duration is not fixed;
- tick measures representational granularity, not seconds.

---

## 3. Coarsener responsibilities

1. Select current detail level (`Ln`).
2. Interpret execution time into global ticks.
3. Trigger coarsen/refine transitions.
4. Activate/deactivate temporary links.
5. Advance global time.

The coarsener does not directly manage compute nodes and does not synchronize them via barriers.

---

## 4. Coarsener is not scheduler

Classical scheduler:
- dispatches tasks;
- waits for acknowledgements;
- is execution-time centric.

DETM coarsener:
- controls time scale;
- does not require acknowledgements;
- operates in global ticks only;
- does not reason in wall-clock seconds.

---

## 5. Time scale as model parameter

Observed time scale for level `Ln` is defined by observation windows in base ticks
(`window_ticks`, `publish_stride_ticks`).

Principle:
- larger spatial scale => longer effective tick;
- smaller scale => shorter effective tick.

This preserves space-time coupling used by level scaling/refinement.

---

## 6. Global time progression

Discrete update:

```text
Tg = Tg + 1
```

Each increment:
- executes one step at current level;
- activates links whose interval includes this tick;
- checks representability invariants.

Global time is monotonic.

---

## 7. Coarsener and refinement

The coarsener:
- detects invariant violation (`E in [0,1]`);
- triggers local refinement;
- decides when refined result can be folded back.

Refinement is not a second clock. It runs inside current global tick semantics.

---

## 8. Coarsener and temporal links

All links:
- are defined in base ticks;
- are activated/deactivated by the coarsener;
- are interpreted through current time scale.

Changing level preserves semantic duration, even if wall-clock duration changes.

---

## 9. Asynchrony model

Asynchrony is provided by:
- no completion synchronization between nodes;
- no global barrier;
- interaction through global time, links, and snapshots.

Coarsener is the only time-consistency point.

---

## 10. Relation to ComfyUI

In ComfyUI integration:
- graph expresses data/intention dependencies;
- coarsener remains out of graph;
- graph execution does not define global-time progression.

---

## 11. Mechanism invariants

1. Global time is discrete and monotonic.
2. Coarsener is not wall-clock driven.
3. No ack dependency.
4. Time scale is tied to level `Ln`.
5. Compatible with refinement and links.

---

## 12. Purpose of this card

This card fixes canonical global-time semantics and the coarsener role in DETM.

