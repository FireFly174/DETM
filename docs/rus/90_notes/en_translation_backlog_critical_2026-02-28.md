# RU -> EN Translation Backlog (Critical-First)

Scope: `docs/rus/**` to `docs/eng/**` translation drift remediation.

Policy:
- RU remains canonical source-of-truth.
- EN remains derivative translation layer.
- Priority is architecture and integration-critical docs first.

Snapshot (2026-02-28):
- RU markdown files scanned: `104`
- EN mirror matches detected: `54`
- Missing EN counterparts: `50`

## Priority P1 (Architecture + Integration)

| RU canonical path | Expected EN target | Why first |
|---|---|---|
| `docs/rus/ROADMAP.md` | `docs/eng/00_overview/roadmap.md` (new) | Canon roadmap availability in EN |
| `docs/rus/ROADMAP_HUMAN.md` | `docs/eng/00_overview/roadmap_human.md` (new) | Human-readable roadmap parity |
| `docs/rus/30_architecture/runtime_api.md` | `docs/eng/30_architecture/runtime_api.md` (new dir) | Runtime contract reference |
| `docs/rus/30_architecture/commit_protocol.md` | `docs/eng/30_architecture/commit_protocol.md` | Cross-node consistency contract |
| `docs/rus/30_architecture/detm_run_migration.md` | `docs/eng/30_architecture/detm_run_migration.md` | Migration guidance for runtime split |
| `docs/rus/30_architecture/OuterFields_and_Subscriptions.md` | `docs/eng/30_architecture/OuterFields_and_Subscriptions.md` | Subscription and boundary semantics |
| `docs/rus/30_architecture/level_policy.md` | `docs/eng/30_architecture/level_policy.md` | Policy behavior and level transitions |
| `docs/rus/30_architecture/Level_policy_schema.md` | `docs/eng/30_architecture/Level_policy_schema.md` | Policy schema contract |
| `docs/rus/30_architecture/target_architecture_synthesis.md` | `docs/eng/30_architecture/target_architecture_synthesis.md` | Target architecture alignment |
| `docs/rus/30_architecture/TimeOperator.md` | `docs/eng/30_architecture/TimeOperator.md` | Time transfer operator semantics |
| `docs/rus/30_architecture/TimeLevelsInvariants.md` | `docs/eng/30_architecture/TimeLevelsInvariants.md` | Invariant definitions across levels |
| `docs/rus/30_architecture/Universal_Entry_via_Coarsen_Refine.md` | `docs/eng/30_architecture/Universal_Entry_via_Coarsen_Refine.md` | Canonical entry/migration logic |

## Priority P2 (Governance and Model Notes)

| RU canonical path | Expected EN target | Why second |
|---|---|---|
| `docs/rus/90_notes/book_concepts_single_source.md` | `docs/eng/90_notes/book_concepts_single_source.md` | Canon vs book framing boundary |
| `docs/rus/90_notes/learning_model_detm.md` | `docs/eng/90_notes/learning_model_detm.md` | Learning/readout model alignment |
| `docs/rus/90_notes/readout_protocol_and_antigoodhart.md` | `docs/eng/90_notes/readout_protocol_and_antigoodhart.md` | Anti-Goodhart readout protocol |
| `docs/rus/RenormalizationCanon.md` | `docs/eng/RenormalizationCanon.md` | Canonical conceptual baseline |

## Priority P3 (Long Tail)

- Remaining missing counterparts are mostly in `docs/rus/90_notes/*` and secondary architecture notes.
- Maintain as rolling backlog unless they become required for external EN consumers.

## Tracking Contract

For each translated file:
- Keep canonical reference to RU source path in front matter or top note.
- Mark EN file as `derivative`.
- Do not reinterpret canon claims when translating.
