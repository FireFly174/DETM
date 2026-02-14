# Snapshots and state visibility

## Status

Canonical mechanism specification.

Note: first-pass translation of `docs/rus/20_mechanisms/snapshots_and_state_visibility.md`.

This card defines the snapshot mechanism that provides consistent state visibility in DETM without acknowledgements or synchronous barriers.

---

## 1. Consistency problem in asynchronous systems

In an asynchronous runtime it is undesirable to:
- wait for every node completion;
- enforce global barriers;
- require per-step processing acknowledgements.

Yet components must:
- observe consistent state;
- know model-time alignment of that state;
- avoid half-updated reads.

Snapshots solve this.

---

## 2. Snapshot definition

Snapshot is an immutable representation of system state at a fixed global tick.

Properties:
- immutable;
- bound to one `global tick`;
- reflects completed dynamics step;
- safely readable by many consumers.

Snapshot is a state artifact, not a process.

---

## 3. Snapshot lifecycle

At each global tick:
1. coarsener initiates step;
2. active links are applied;
3. mandatory refinements are executed;
4. snapshot is formed;
5. snapshot is published for reading.

Published snapshot never mutates.

---

## 4. State visibility rule

Components do not read live mutable state.
They read snapshots only.

This guarantees:
- no read/write races;
- no extra lock protocol for observers;
- consistent observation baseline.

Readers may:
- consume latest snapshot;
- request a specific tick snapshot;
- skip intermediate snapshots.

---

## 5. "Everyone must know" without ack

"Everyone knows" means:

> everyone can access the same published snapshot.

It does not mean:
- everyone processed it;
- everyone reacted to it;
- everyone finished computation.

Publication is sufficient consistency primitive.

---

## 6. Snapshot and global time

Each snapshot should include:
- global tick id;
- level id (`Ln`);
- digest/hash;
- reference to state payload.

This provides strict temporal ordering and level-transition continuity.

---

## 7. Snapshot and asynchrony

Asynchrony is preserved because:
- publishing does not block further stepping;
- reading does not affect dynamics;
- readers can lag/lead in wall-clock time.

Only global tick is a required synchronization coordinate.

---

## 8. ComfyUI relation

In ComfyUI integration:
- nodes consume snapshots, not live internals;
- visualization/analysis/export uses snapshots;
- graph execution does not control snapshot publication semantics.

---

## 9. Snapshot storage

Snapshots may be stored:
- in process memory;
- on device memory as read-only blobs;
- on disk as logs/archives.

Storage format is implementation-specific as long as immutability holds.

---

## 10. Mechanism invariants

1. Snapshot is immutable after publish.
2. Snapshot maps to exactly one global tick.
3. Reading does not block stepping.
4. No acknowledgements or barriers are required.
5. All observers see the same artifact for a given tick.

---

## 11. Purpose of this card

This card fixes canonical consistent-visibility semantics in DETM.

