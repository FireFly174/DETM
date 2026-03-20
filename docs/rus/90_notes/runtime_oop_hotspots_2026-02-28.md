# DETM Runtime OOP Hotspots

- Generated at: `2026-03-01T00:05:48`
- Roots: `D:/github/DETM/detm, D:/github/DETM/detm_app`
- Python files scanned: `236`

## Policy Limits

| Metric | Threshold |
|---|---:|
| file_loc | 120 |
| function_loc | 70 |
| class_methods | 15 |
| max_imports | 25 |
| nesting | 4 |

## Hotspot Summary

- Hotspots: `99`
- Structural violations (layering + cycles + syntax): `89`
- Import cycles: `0`

## Hotspot Table

| id | path | layer | severity | breaches | cycle | refactor_hint |
|---|---|---|---|---:|---|---|
| `HS-101` | `detm/runtime/refinement/pipeline/detect.py` | `service` | `P1` | 3 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-208` | `detm_app/ui/napari/interactive/flow/render.py` | `adapter_transport` | `P1` | 4 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-003` | `detm/analysis/boundary_flux.py` | `service` | `P1` | 2 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-046` | `detm/runtime/fabric/handshake_recorder_config/flow.py` | `service` | `P1` | 2 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-055` | `detm/runtime/fabric/runtime_composer/composer.py` | `service` | `P1` | 3 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-082` | `detm/runtime/level_policy/normalization_build.py` | `service` | `P1` | 2 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-100` | `detm/runtime/refinement/pipeline/correction.py` | `service` | `P1` | 2 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-102` | `detm/runtime/refinement/pipeline/metrics.py` | `service` | `P1` | 2 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-122` | `detm_app/runner/headless/main.py` | `orchestration` | `P1` | 2 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-125` | `detm_app/runner/headless/options_fabric/coordination.py` | `orchestration` | `P1` | 2 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-129` | `detm_app/runner/headless/options_fabric/transport.py` | `orchestration` | `P1` | 2 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-136` | `detm_app/runner/headless/parser_fabric/handshake.py` | `orchestration` | `P1` | 2 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-137` | `detm_app/runner/headless/parser_fabric/transport.py` | `orchestration` | `P1` | 2 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-141` | `detm_app/runner/headless/subscribers/fabric.py` | `orchestration` | `P1` | 2 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-152` | `detm_app/runtime/session/adaptive.py` | `orchestration` | `P1` | 2 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-154` | `detm_app/runtime/session/step_flow.py` | `orchestration` | `P1` | 2 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-163` | `detm_app/runtime/subscribers/fabric/attach.py` | `orchestration` | `P1` | 2 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-176` | `detm_app/runtime/subscribers/watch/flow.py` | `orchestration` | `P1` | 2 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-177` | `detm_app/runtime/subscribers/watch/operator_decisions.py` | `orchestration` | `P1` | 2 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-181` | `detm_app/runtime/ui_runtime/core.py` | `orchestration` | `P1` | 2 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-183` | `detm_app/runtime/ui_runtime/learning.py` | `orchestration` | `P1` | 2 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-204` | `detm_app/ui/napari/interactive/flow/controls_parts/view_runtime/runtime.py` | `adapter_transport` | `P1` | 2 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-205` | `detm_app/ui/napari/interactive/flow/controls_parts/view_runtime/view.py` | `adapter_transport` | `P1` | 2 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-213` | `detm_app/ui/napari/lab.py` | `adapter_transport` | `P1` | 3 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-037` | `detm/runtime/fabric/delivery/replicated.py` | `service` | `P1` | 3 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-038` | `detm/runtime/fabric/delivery_tracking/flow.py` | `service` | `P1` | 1 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-042` | `detm/runtime/fabric/epoch_consensus/flow.py` | `service` | `P1` | 2 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-044` | `detm/runtime/fabric/handshake/flow.py` | `service` | `P1` | 1 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-066` | `detm/runtime/fabric/tcp_transport/relay.py` | `service` | `P1` | 1 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-081` | `detm/runtime/level_policy/model.py` | `service` | `P1` | 1 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-113` | `detm/runtime/watch_contract.py` | `service` | `P1` | 1 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-186` | `detm_app/ui/napari/interactive/__init__.py` | `adapter_transport` | `P1` | 4 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-206` | `detm_app/ui/napari/interactive/flow/graph.py` | `adapter_transport` | `P1` | 1 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-214` | `detm_app/ui/napari/subscriber_flow.py` | `adapter_transport` | `P1` | 2 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-219` | `detm_app/ui/tk/runner/flow/batch.py` | `adapter_transport` | `P1` | 2 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-233` | `detm_app/ui/tk/runner/flow/viz/flow.py` | `adapter_transport` | `P1` | 2 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-052` | `detm/runtime/fabric/quorum_runtime_flow.py` | `service` | `P1` | 1 | no | Restore dependency direction with port/interface boundaries between layers |
| `HS-155` | `detm_app/runtime/subscribers/__init__.py` | `orchestration` | `P1` | 1 | no | Restore dependency direction with port/interface boundaries between layers |
| `HS-162` | `detm_app/runtime/subscribers/fabric/__init__.py` | `orchestration` | `P1` | 1 | no | Restore dependency direction with port/interface boundaries between layers |
| `HS-193` | `detm_app/ui/napari/interactive/flow/batch/request.py` | `adapter_transport` | `P1` | 1 | no | Restore dependency direction with port/interface boundaries between layers |
| `HS-194` | `detm_app/ui/napari/interactive/flow/batch/state.py` | `adapter_transport` | `P1` | 1 | no | Restore dependency direction with port/interface boundaries between layers |
| `HS-226` | `detm_app/ui/tk/runner/flow/layout.py` | `adapter_transport` | `P1` | 1 | no | Restore dependency direction with port/interface boundaries between layers |
| `HS-004` | `detm/analysis/fields.py` | `service` | `P2` | 2 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-051` | `detm/runtime/fabric/quorum_runtime_factory.py` | `service` | `P2` | 2 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-074` | `detm/runtime/influence/apply.py` | `service` | `P2` | 2 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-128` | `detm_app/runner/headless/options_fabric/handshake.py` | `orchestration` | `P2` | 2 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-133` | `detm_app/runner/headless/parser_fabric/coordination.py` | `orchestration` | `P2` | 2 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-134` | `detm_app/runner/headless/parser_fabric/delivery.py` | `orchestration` | `P2` | 2 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-184` | `detm_app/runtime/ui_runtime/recording.py` | `orchestration` | `P2` | 2 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-198` | `detm_app/ui/napari/interactive/flow/controls_parts/influence/joystick.py` | `adapter_transport` | `P2` | 2 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-199` | `detm_app/ui/napari/interactive/flow/controls_parts/influence/page.py` | `adapter_transport` | `P2` | 2 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-222` | `detm_app/ui/tk/runner/flow/controls/influence.py` | `adapter_transport` | `P2` | 2 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-005` | `detm/analysis/grid_timeseries.py` | `service` | `P2` | 1 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-007` | `detm/core/entropy.py` | `domain` | `P2` | 1 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-008` | `detm/core/fields.py` | `domain` | `P2` | 1 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-009` | `detm/core/invariants.py` | `domain` | `P2` | 1 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-011` | `detm/integrations/acgs_backend.py` | `infrastructure` | `P2` | 1 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-015` | `detm/metrics/boundary_flux.py` | `service` | `P2` | 1 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-023` | `detm/runtime/api/step_flow.py` | `service` | `P2` | 1 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-027` | `detm/runtime/backends/torch_backend.py` | `service` | `P2` | 1 | no | Extract long functions into focused helpers/use-case units |
| `HS-029` | `detm/runtime/commit_packet.py` | `service` | `P2` | 1 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-031` | `detm/runtime/config/model.py` | `service` | `P2` | 1 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-035` | `detm/runtime/fabric/ack.py` | `service` | `P2` | 1 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-047` | `detm/runtime/fabric/handshake_recorder_config/helpers.py` | `service` | `P2` | 1 | no | Flatten control flow using guard clauses and strategy helpers |
| `HS-049` | `detm/runtime/fabric/quorum_runtime.py` | `service` | `P2` | 1 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-050` | `detm/runtime/fabric/quorum_runtime_coordination.py` | `service` | `P2` | 1 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-059` | `detm/runtime/fabric/runtime_composer/reporting.py` | `service` | `P2` | 1 | no | Extract long functions into focused helpers/use-case units |
| `HS-065` | `detm/runtime/fabric/tcp_transport/flow.py` | `service` | `P2` | 1 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-079` | `detm/runtime/level_policy/decision_runtime_adaptive.py` | `service` | `P2` | 1 | no | Extract long functions into focused helpers/use-case units |
| `HS-080` | `detm/runtime/level_policy/decision_signals.py` | `service` | `P2` | 1 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-084` | `detm/runtime/level_policy/normalization_serialize.py` | `service` | `P2` | 1 | no | Extract long functions into focused helpers/use-case units |
| `HS-085` | `detm/runtime/outerfields.py` | `service` | `P2` | 1 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-088` | `detm/runtime/pattern_memory/flow.py` | `service` | `P2` | 1 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-090` | `detm/runtime/pattern_memory/runtime.py` | `service` | `P2` | 1 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-099` | `detm/runtime/refinement/pipeline/contracts.py` | `service` | `P2` | 1 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-103` | `detm/runtime/refinement/pipeline/operator_contract.py` | `service` | `P2` | 1 | no | Extract long functions into focused helpers/use-case units |
| `HS-104` | `detm/runtime/refinement/pipeline/orchestrator.py` | `service` | `P2` | 1 | no | Extract long functions into focused helpers/use-case units |
| `HS-110` | `detm/runtime/signature.py` | `service` | `P2` | 1 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-111` | `detm/runtime/state.py` | `service` | `P2` | 1 | no | Split file by responsibility into submodules and keep public surface thin |
| `HS-118` | `detm_app/runner/batch_service.py` | `orchestration` | `P2` | 1 | no | Split file by responsibility into submodules and keep public surface thin |

Truncated view: showing first 80 of 99 hotspots.

## Import Cycles

- No import cycles detected.
