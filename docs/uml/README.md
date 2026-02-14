# UML Diagrams

This folder contains project UML in PlantUML format (`.puml`).

## Navigation

### One-file aggregate
- `ALL_PROJECT_UML.puml` - all UML blocks in a single PlantUML document.
- `ALL_PROJECT_UML_MEGA.puml` - one large single-diagram view of the whole project.
- `ALL_PROJECT_UML_MEGA.puml` is refreshed for current package layout (`session/*`, `ui_runtime/*`, `subscribers/*`, `serialization/*`, `fabric/*`) as of `2026-02-14`.

Note:
- In `ALL_PROJECT_UML.puml`, PlantUML preview usually shows one `@startuml ... @enduml` block at a time (depends on cursor position).
- If you need everything in one canvas immediately, open `ALL_PROJECT_UML_MEGA.puml`.

### Quick start (existing compact set)
- `01_system_context.puml`
- `02_runtime_tick_sequence.puml`
- `03_napari_interactive_flow.puml`
- `04_tk_runner_flow.puml`

### Full detailed set
- `architecture/00_two_minute_explainer.puml`
- `architecture/01_repository_package_map.puml`
- `architecture/02_entrypoints_and_modes.puml`
- `runtime/01_core_domain_model.puml`
- `runtime/02_app_runtime_static.puml`
- `runtime/03_session_step_sequence.puml`
- `runtime/04_tick_scheduler_sequence.puml`
- `runtime/05_subscribers_matrix.puml`
- `runtime/06_influence_merge_semantics.puml`
- `runtime/07_l0_tick_state_machine.puml`
- `runtime/08_eventbus_sync_contract.puml`
- `runtime/09_runtime_adaptive_window_state_machine.puml`
- `runtime/10_runtime_adaptive_telemetry_sequence.puml`
- `runtime/11_policydecision_runtime_adaptive_class.puml`
- `runner/01_headless_components.puml`
- `runner/02_headless_run_sequence.puml`
- `runner/03_shell_router_sequence.puml`
- `ui/01_napari_lab_sequence.puml`
- `ui/02_napari_interactive_detailed.puml`
- `ui/03_tk_runner_detailed.puml`
- `transport/01_viz_transport_components.puml`
- `transport/02_viz_message_sequence.puml`
- `fabric/01_namespace_map.puml`
- `fabric/02_runtime_composition.puml`
- `fabric/03_commit_ack_quorum_sequence.puml`
- `fabric/04_complexity_hotspots.puml`

## Recommended reading order
1. `ALL_PROJECT_UML.puml`
2. `architecture/00_two_minute_explainer.puml`
3. `architecture/01_repository_package_map.puml`
4. `architecture/02_entrypoints_and_modes.puml`
5. `runtime/01_core_domain_model.puml`
6. `runtime/02_app_runtime_static.puml`
7. `runtime/06_influence_merge_semantics.puml`
8. `runtime/07_l0_tick_state_machine.puml`
9. `runtime/08_eventbus_sync_contract.puml`
10. `runtime/09_runtime_adaptive_window_state_machine.puml`
11. `runtime/10_runtime_adaptive_telemetry_sequence.puml`
12. `runtime/11_policydecision_runtime_adaptive_class.puml`
13. `runner/02_headless_run_sequence.puml`
14. `ui/01_napari_lab_sequence.puml`
15. `fabric/01_namespace_map.puml`
16. `fabric/03_commit_ack_quorum_sequence.puml`
17. `fabric/04_complexity_hotspots.puml`

## Explicit contracts (from current code)

- Influence merge: deterministic by scheduler order (`tick`, then insertion `order`), but not commutative for the same override key (`last write wins`).
- Chunk merge (`_merge_observables`): events are concatenated in chunk order, cost values are summed by key, signature/quality/field summaries are taken from the last chunk.
- EventBus: synchronous, listeners called in subscription order; heavy listeners can block publish/tick path.

## VS Code setup

Recommended extension:
- `jebbs.plantuml` (PlantUML)

Quick setup (server render):
1. Install `jebbs.plantuml`.
2. Add to VS Code settings JSON:

```json
{
  "plantuml.render": "PlantUMLServer",
  "plantuml.server": "https://www.plantuml.com/plantuml"
}
```

3. Open any `.puml` and run `PlantUML: Preview Current Diagram` (`Alt+D` in many setups).

## Optional local render

Use local mode if you want offline preview:
- install Java
- install Graphviz (`dot` in `PATH`)
- set `"plantuml.render": "Local"`

## Export

From command palette:
- `PlantUML: Export Current Diagram`

Suggested output dir:
- `docs/uml/out/`
