# ROADMAP

Обновлено: 2026-02-12

## Цель

Зафиксировать фактическое состояние DETM и поэтапный план миграции к целевой архитектуре,
чтобы между сессиями не терялся контекст: что уже работает, что является переходным контуром,
и что критично довести до production-уровня.

## Легенда

- `[x]` сделано
- `[ ]` запланировано или в работе

## Checkup (снимок состояния)

- [x] Канонический L0 runtime API (`reset/step/digest/serialize/deserialize`)
- [x] Бэкенды `numpy` и `torch` (в т.ч. `device=cuda` при доступности)
- [x] Слой оркестрации внутри `detm/run`: `Session + EventBus + TickScheduler + TickRunner`
- [x] Invariant streams/coarsening (`InvariantCoarsener`, `invariants.jsonl`)
- [x] Сериализация state: `msgpack + npz`
- [x] Артефакты запуска: `state.msgpack`, `trace.jsonl`, `commits.jsonl`, `commits_audit.jsonl` (policy-driven), `commit_validation.json`, `history.jsonl`, `fields_hist.npz`, `catalog.json`
- [x] OuterFields V1 вычислитель в коде (`detm/runtime/outerfields.py`)
- [x] Интеграции: `runtime_bridge`, `ACGSDetmBackend`
- [x] Рабочая визуализация: `Tk` + `embedded/tcp` transport
- [x] Тестовый snapshot: `pytest -q -> 214 passed, 1 skipped`
- [x] Зафиксирован архитектурный вектор: текущий путь переходный, target-архитектура обязательна
- [x] Выделенный пакет `detm_app` (orchestration перенесён; `detm/run/*` оставлен как compatibility facade)
- [x] Поднят совместимый `detm_app` shim-пакет (`bus/session/scheduler/coarsening`) как migration-step этапа A без ломки API
- [x] Entry points (`detm/cli.py`, `detm/ui/tk_runner.py`) переведены на app-layer импорты `detm_app.*` для `session/bus/coarsening`
- [x] `main.py` и `detm.py` используют канонические entrypoints `detm_app.cli`/`detm_app.tk_runner`; `detm/cli.py`, `detm/ui/tk_runner.py`, `detm/ui/config_hints.py`, `detm/ui/tooltips.py` оставлены как deprecated compatibility facades
- [x] Рабочий контур кода/тестов переведён на `detm_app.*`; `detm/run/*` остаётся только как compatibility facade
- [x] `detm/run/*` переведён в lazy/deprecated compatibility facade (`DeprecationWarning` + lazy export resolution), чтобы `detm` оставался библиотечным слоем без eager-зависимости от `detm_app`
- [x] Зафиксирован deprecation-policy для `detm/run/*` (removal target `0.3.0`, дата `2026-06-30`, миграционный гайд `docs/rus/30_architecture/detm_run_migration.md`)
- [x] Добавлен CI-guard на новые импорты `detm.run.*` вне compatibility слоя (`tests/test_no_detm_run_imports.py`)
- [x] Добавлен CI-guard на новые импорты legacy entrypoints `detm.cli`/`detm.ui.*`/`detm.viz.*` вне compatibility слоя (`tests/test_no_legacy_entrypoint_imports.py`)
- [x] Централизованный runtime-контур `LevelPolicy` (schema + runtime usage + trace policy fields + microsteps/batch/publish wiring + multi-signal runtime adaptive tuning + directional delta-mode + auto profile selection + anti-flap cooldown + sampled/aggregated runtime-adaptive telemetry в trace/watch policy + runtime adaptive guardrails `min/max + reject_unsafe`)
- [x] Расширены runtime observability профили (`adaptive_signal_event_types`, `adaptive_detail_mode`, `adaptive_hold_ticks`, `adaptive_allowed_event_types`) + signal-driven переключение в session runtime
- [x] Рабочий `refinement` MVP (detectors `energy_overflow` + `state_nonfinite` + `capacity_pressure` -> локальный ROI/sanitize correction -> trace event; capacity detector policy-driven, multi-signal, temporal/memory-driven, learned/cross-level, operator-driven/cross-node, distributed/signed, cryptographic/consensus-grade, attestation/Byzantine-grade)
- [x] Контур памяти паттернов MVP (`PatternStore` file-backed stub + `PatternCache` LRU/TTL + lookup before refine + pruning thresholds + quality-gated reuse по `error/deviation` + policy-driven scope `global|portable|strict` для переносимости между уровнями/режимами)
- [x] Разделение трассировки: `System Trace` (`trace.jsonl`) + `Watch Trace` (`watch_trace.jsonl`) как проекции
- [x] `trace_ref`-дисциплина в trace/watch/commit проекциях
- [x] Базовая storage policy для trace (`retention-window`, `compaction-budget`) в runtime/subscribers
- [x] L0 artifact storage policy расширена на ключевые артефакты (`trace/watch_trace/watch_contract/outerfields/commits/commits_audit/history/invariants/commit_validation/fabric_acks/fabric_ack_envelopes/fabric_delivery_acks/fabric_dead_letters/fabric_quorum_report`)
- [x] Multi-level fallback для artifact storage policy (`L2 -> L1 -> L0 -> default/*`) + e2e coverage для `active_level=L1/L2`
- [x] Production watch-contract (`watch_contract.jsonl` + `outerfields/*.npz` + `OuterFieldsRef` linkage с `trace_ref`)
- [x] Каноническая napari-интеграция (read-only subscriber path через `detm_app/napari_subscriber.py`)
- [x] Добавлен endpoint-registry для napari auto-discovery (`runs/viz_endpoint.json`) + cleanup stale endpoint при закрытии локального viz-daemon
- [x] Расширен тестовый napari coverage для read-only path (`endpoint resolution/precedence`, `poll timeout`, `layer presenter update/autoscale`, `multi-level active_level meta`)
- [x] Для дополнительных runtime-отчётов добавлены policy-driven history контуры (`commit_validation_history.jsonl`, `fabric_quorum_report_history.jsonl`) с multi-level retention
- [ ] N-мерное обобщение runtime
- [x] `CommitPacket` schema MVP в runtime (`detm/runtime/commit_packet.py`) + валидация
- [x] Локальный validator-отчёт для commit-потока (`commit_validation.json`: chain/proof/watermark checks)
- [x] Проведён обзор transport/packet паттернов из `D:\github\game\references\old_repo\lib` с привязкой к этапу G (`Node/Fabric`)
- [x] Добавлены MVP-контракты node/fabric: `FabricEnvelope`, `CommitChainManager`, `ProofAck/TrustAck`, `InMemoryFabricBus`
- [x] Добавлен local handshake wiring в runtime pipeline (`commit_packet -> ProofAck/TrustAck`) как opt-in контур
- [x] Добавлены quorum/retry policy primitives для fabric (`BasicQuorumPolicy`, `ValidatorSetQuorumPolicy`, `RetryPolicy`, local coordinator report)
- [x] Добавлен TCP fabric transport adapter (`TcpFabricTransport` + `TcpFabricRelay`) как network MVP
- [x] Добавлены `StaticValidatorRegistry` и `pending-timeout` окно в quorum coordinator (`fabric_quorum_report.json`)
- [x] Добавлен distributed handshake bridge по `payload_inline` (`commit/ack`) для network MVP без shared artifact storage
- [x] Добавлен file-backed shared artifact resolver (`FileFabricArtifactStore`) для commit/ack в node/fabric MVP
- [x] Добавлен `InMemoryEpochWatermarkCoordinator` и wiring в handshake (`commit -> epoch/watermark gate -> proof/trust ack`)
- [x] Добавлен replay-check sampling в `LocalFabricValidator` + runtime wiring/reporting (`replay_sampling` в `fabric_quorum_report.json`)
- [x] Добавлен shared-state `FileEpochWatermarkCoordinator` (межнодовый MVP через общий `epoch_state.json`)
- [x] Добавлен lock-контур для `FileEpochWatermarkCoordinator` (`lock timeout`, `stale lock cleanup`) для межпроцессной синхронизации
- [x] Добавлен `ReplicatedFileEpochWatermarkCoordinator` (read/write quorum по нескольким `epoch_state` репликам)
- [x] Добавлен transport pre-consensus coordinator для `epoch` (`epoch_proposal/epoch_vote`, quorum timeout/policy)
- [x] Добавлен mode-split routing для node/fabric handshake (`realtime/audit` каналы для `commit/ack`, опционально через policy-флаг)
- [x] Добавлен file-backed delivery outbox для fabric envelope (`undelivered -> queue -> flush/retry`) и runtime wiring в handshake/recorder
- [x] Добавлена backpressure overflow policy для delivery outbox (`audit_first|oldest|newest`) с приоритетом сохранения `realtime` при перегрузке
- [x] Добавлен live transport backpressure adapter (`BufferedFabricTransport`: `block/drop_oldest/drop_newest/fail`) и runtime wiring в fabric handshake
- [x] Добавлен acknowledged-delivery MVP для `commit` envelope (`delivery_id` + `delivery_ack` channel + retry/timeout receipt tracking + validator-set/reject policy)
- [x] Commit-delivery wiring вынесен в runtime service (`FabricCommitDeliveryService`), subscriber-слой оставлен как orchestration-boundary
- [x] Commit-ingress wiring вынесен в runtime service (`FabricCommitIngressService`), subscriber-слой оставлен как orchestration-boundary
- [x] Ack-ingress wiring вынесен в runtime service (`FabricAckIngressService`), subscriber-слой оставлен как orchestration-boundary
- [x] Quorum policy/registry composition вынесена в runtime service (`FabricQuorumRuntimeService`), subscriber-слой оставлен как orchestration-boundary
- [x] Сборка `fabric_quorum_report` вынесена в runtime builder (`FabricQuorumReportBuilder`), subscriber-слой оставлен как orchestration-boundary
- [x] Запись `fabric_acks/fabric_delivery_acks/fabric_quorum_report/fabric_dead_letters` вынесена в runtime writer (`FabricRuntimeReportWriter`)
- [x] Lifecycle wiring (`start/stop`) fabric runtime-компонентов вынесен в runtime bundle (`FabricHandshakeRuntimeBundle`)
- [x] Сборка fabric runtime-компонентов вынесена в composer/factory (`compose_fabric_handshake_runtime`)
- [x] Commit/ack artifact-resolve + replay-check выведены в runtime adapter (`FabricArtifactResolver`)
- [x] Mode-channel и runtime-bundle startup helper-функции вынесены в `fabric_runtime_helpers.py`
- [x] Нормализация `FabricHandshakeRecorder.attach(...)` вынесена в runtime-config helper (`normalize_fabric_handshake_recorder_attach_kwargs`)

## Зафиксированные архитектурные решения

- [x] L0 runtime остаётся UI-агностичным.
- [x] Внешние потребители должны работать через артефакты/контракты, а не через прямой доступ к живому state.
- [x] `OuterFields` и подписки являются основным интерфейсом межуровневой/внешней наблюдаемости.
- [x] `Tk + TCP/embedded` — текущий рабочий контур визуализации; napari — migration track.
- [x] По умолчанию используется минимальный режим observables; тяжёлые CPU-пути должны оставаться opt-in.
- [x] Текущая структура кода трактуется как transition, а не как финальная архитектура.
- [x] Псевдоцели (релятивистская оптика, физический мотив структур, агент навыков) учитываются как источник гипотез, но не как KPI фазы.
- [x] Целевая модель трассировки: `System Trace` (канонический журнал) + `Watch Trace` (операторские/исследовательские watchpoints как проекции).
- [x] Любая внешняя проекция/уведомление обязана нести `trace_ref` на committed артефакт.
- [x] Наблюдаемость управляется policy-driven профилями runtime (`allowed_event_types`, `detail_mode`).
- [x] Политика хранения артефактов задаётся по уровням `L0..Ln` через `retention-window` и `compaction-budget`.
- [x] Архитектурные описания “динамика как прямой эфир” и “модульный runtime-стек” зафиксированы как единый north-star: `docs/rus/30_architecture/target_architecture_synthesis.md`.
- [x] Межнодовая синхронизация фиксируется по `GlobalTick/commit boundary` (epoch/watermark), а не по внутренним microsteps нод.
- [x] Для node/fabric принят OOP-подход с жёстким разделением ролей: contract classes, chain/lifecycle classes, validators, transport adapters.
- [x] Введены архитектурные `ARCH-MARKERS` в коде (`LAYER_BAND`, `ABSTRACT_DISTANCE`, `OOP_TECH_DEBT`) для явной фиксации расстояния до абстракций.

## Что уже реализовано (по модулям)

- [x] `detm/runtime/api.py`: публичный L0 API, выбор backend, digest/observables.
- [x] `detm/runtime/backends/*`: `NumpyBackend`, `TorchBackend`.
- [x] `detm/runtime/level_policy.py`: schema + policy decision (`microsteps/commit_stride/observability profile`).
- [x] `detm/runtime/commit_packet.py`: machine-validatable `CommitPacket/CommitTickRef` (`state|boundary|coarsened|proof`, `realtime|audit`).
- [x] `detm/runtime/fabric_validation.py`: local commit validation (`chain/proof checks`, `epoch/watermark` report).
- [x] `detm/runtime/fabric_envelope.py`: transport envelope (`message_type/channel/mode/payload_ref`) + optional `payload_inline` bridge для node/fabric.
- [x] `detm/runtime/commit_chain.py`: `CommitChainManager` (`sequence/verify/accept`, `tail -> parent_ref`).
- [x] `detm/runtime/fabric_ack.py`: `ProofAck/TrustAck` contract classes (validator acknowledgements).
- [x] `detm/runtime/fabric_transport.py`: `InMemoryFabricBus` + `BufferedFabricTransport` (live backpressure adapter).
- [x] `detm/runtime/fabric_validator.py`: `FabricValidator` protocol + `LocalFabricValidator` (`chain checks + replay sampling policy`).
- [x] `detm/runtime/fabric_handshake.py`: `FabricHandshakeService` (`commit envelope -> proof/trust ack envelope`, mode-aware channel routing + `delivery_ack` emission).
- [x] `detm/runtime/fabric_delivery.py`: `FabricEnvelopeOutbox`, `JsonlFabricEnvelopeOutbox` (durable queue + flush/retry).
- [x] `detm/runtime/fabric_delivery_receipts.py`: `Count/ValidatorSet` delivery policies + `InMemoryDeliveryReceiptCoordinator`.
- [x] `detm/runtime/fabric_delivery_tracking.py`: retry/timeout state-machine `DeliveryTrackingCoordinator` (runtime-layer extraction from subscribers).
- [x] `detm/runtime/fabric_commit_delivery.py`: `FabricCommitDeliveryService` (commit publish/retry/outbox + `delivery_ack` subscriptions + delivery tracking wiring).
- [x] `detm/runtime/fabric_commit_ingress.py`: `FabricCommitIngressService` (commit packet ingress -> artifact resolve -> envelope publish через runtime delivery service).
- [x] `detm/runtime/fabric_ack_ingress.py`: `FabricAckIngressService` (proof/trust `ack` subscriptions + ingress forwarding в quorum-coordinator).
- [x] `detm/runtime/fabric_quorum_runtime.py`: `FabricQuorumRuntimeService` (policy selection + validator registry + quorum snapshot composition).
- [x] `detm/runtime/fabric_quorum_report.py`: `FabricQuorumReportBuilder` (runtime-композиция секций `fabric_quorum_report.json`).
- [x] `detm/runtime/fabric_report_writer.py`: `FabricRuntimeReportWriter` (запись ack/envelope/dead-letter артефактов и `fabric_quorum_report.json`).
- [x] `detm/runtime/fabric_runtime_bundle.py`: `FabricHandshakeRuntimeBundle` (lifecycle порядок `start/stop` для handshake/ack/delivery/runtime transport).
- [x] `detm/runtime/fabric_runtime_composer.py`: `compose_fabric_handshake_runtime` + `FabricHandshakeRuntimeComposition` (factory сборка runtime-контуров для handshake recorder).
- [x] `detm/runtime/fabric_artifact_resolver.py`: `FabricArtifactResolver` (commit/ack write+resolve + replay-check статистика).
- [x] `detm/runtime/fabric_runtime_helpers.py`: `mode_channels`, `channel_for_mode`, `start_runtime_bundle`.
- [x] `detm/runtime/fabric_handshake_recorder_config.py`: нормализация аргументов `FabricHandshakeRecorder.attach(...)` в отдельный runtime-config helper.
- [x] `detm/runtime/fabric_quorum.py`: `QuorumPolicy`, `BasicQuorumPolicy`, `ValidatorSetQuorumPolicy`, `InMemoryQuorumCoordinator`.
- [x] `detm/runtime/fabric_validator_registry.py`: `ValidatorRegistry`, `StaticValidatorRegistry` (MVP membership source).
- [x] `detm/runtime/fabric_artifact_store.py`: `FabricArtifactStore`, `FileFabricArtifactStore` (durable shared resolver MVP).
- [x] `detm/runtime/fabric_epoch.py`: `FabricEpochCoordinator`, `InMemoryEpochWatermarkCoordinator`, `FileEpochWatermarkCoordinator`, `ReplicatedFileEpochWatermarkCoordinator` (+ lock/quorum policy), `EpochDecision`.
- [x] `detm/runtime/fabric_epoch_consensus.py`: `TransportEpochConsensusCoordinator` (`epoch_proposal/epoch_vote` pre-consensus layer).
- [x] `detm/runtime/fabric_tcp_transport.py`: `TcpFabricTransport`, `TcpFabricRelay`, `open_fabric_transport`.
- [x] `detm/run/subscribers.py`: `FabricHandshakeRecorder` (локальный wiring между `CommitJsonlWriter` и handshake-service, запись `fabric_acks.jsonl`, split-mode channel policy).
- [x] `detm_app/cli.py`: канонический headless entrypoint; `detm/cli.py` — deprecated facade.
- [x] `detm_app/tk_runner.py`: канонический Tk entrypoint; `detm/ui/tk_runner.py` — deprecated facade.
- [x] `detm_app/config_hints.py`, `detm_app/tooltips.py`: канонические UI-helper модули; `detm/ui/config_hints.py`, `detm/ui/tooltips.py` — deprecated facades.
- [x] `detm_app/tk_panel.py`, `detm_app/napari_subscriber.py`: канонические viz-entrypoint модули; `detm/viz/tk_panel.py`, `detm/viz/napari_subscriber.py` — deprecated facades.
- [x] `detm_app/protocol.py`, `detm_app/client.py`, `detm_app/daemon.py`, `detm_app/subscriber.py`, `detm_app/transport.py`: канонический runtime-neutral viz-контур; `detm/viz/*` оставлен только как deprecated compatibility facade слой.
- [x] `detm/runtime/outerfields.py`: `OuterFieldsV1` и базовый вычислитель каналов.
- [x] `detm/runtime/watch_contract.py`: `OuterFieldsRef`, `WatchContractPacket` (artifact-first watch contract).
- [x] `detm/runtime/serialization.py`: pack/unpack state, schema-aware digest.
- [x] `detm/run/session.py`: сессия и event-emission lifecycle.
- [x] `detm/run/scheduler.py`: deterministic tick scheduler и runner.
- [x] `detm/run/coarsening.py`: инвариантные time streams.
- [x] `detm/run/subscribers.py`: writer-ы артефактов, trace, `realtime/audit` commits, invariants, viz streaming.
- [x] `detm/integrations/acgs_backend.py`: stateful adapter для ACGS-stub.
- [x] `detm/ui/tk_runner.py`: deprecated compatibility launcher facade.
- [x] `detm/viz/*`: только deprecated compatibility facades на `detm_app` (без канонической runtime-логики).
- [x] `detm_app/*`: app-layer orchestration (`EventBus`, `DetmSession`, `TickScheduler`, `TickRunner`, coarsening, subscribers); `detm/run/*` оставлен как re-export compatibility layer.

## Что уже реализовано (по документации)

- [x] Канон и механизмы: `docs/rus/10_model/*`, `docs/rus/20_mechanisms/*`.
- [x] Runtime/архитектурные контракты: `docs/rus/30_architecture/runtime_api.md`, `global_tick.md`, `OuterFields_and_Subscriptions.md`, `commit_protocol.md`.
- [x] Гипотезы и эксперименты: `docs/rus/40_hypotheses/*`, `docs/rus/50_experiments/*`.
- [x] Статус-снимок кодовой базы: `docs/rus/90_notes/codebase_spec_2026-02-09.md`.
- [x] Архив архитектурных вариантов: `docs/rus/90_notes/architecture_variants_l0_and_fabric_2026-02-09.md`.
- [x] Инженерный паспорт и target constraints: `docs/rus/90_notes/DETM_solution_passport_filled.md`.
- [x] Книга как единый источник концепций и модель обучения: `book_concepts_single_source.md`, `learning_model_detm.md`, `readout_protocol_and_antigoodhart.md`.
- [x] Синтез целевой архитектуры и привязка `as-is -> to-be`: `docs/rus/30_architecture/target_architecture_synthesis.md`.

## Что уже реализовано (по тестам)

- [x] `tests/test_integration_contract.py`
- [x] `tests/test_golden_contract.py`
- [x] `tests/test_numpy_torch_parity.py`
- [x] `tests/test_energy_invariant.py`
- [x] `tests/test_entropy_dynamics.py`
- [x] `tests/test_invariants.py`
- [x] `tests/test_coarsening.py`
- [x] `tests/test_influence.py`
- [x] `tests/test_boundary_pressure.py`
- [x] `tests/test_marker_passive.py`
- [x] `tests/test_acgs_backend_adapter.py`
- [x] `tests/test_level_policy_runtime.py`
- [x] `tests/test_artifact_storage_policy.py`
- [x] `tests/test_commit_packet_schema.py`
- [x] `tests/test_commit_trace_linkage.py`
- [x] `tests/test_commit_validation_report.py`
- [x] `tests/test_fabric_envelope_and_chain.py`
- [x] `tests/test_fabric_ack_and_transport.py`
- [x] `tests/test_fabric_validator_and_handshake.py`
- [x] `tests/test_fabric_handshake_recorder.py`
- [x] `tests/test_fabric_quorum_and_retry.py`
- [x] `tests/test_fabric_tcp_transport.py`
- [x] `tests/test_fabric_artifact_store.py`
- [x] `tests/test_fabric_epoch.py`
- [x] `tests/test_fabric_epoch_consensus.py`
- [x] `tests/test_fabric_delivery_outbox.py`
- [x] `tests/test_fabric_transport_backpressure.py`
- [x] `tests/test_fabric_delivery_receipts.py`
- [x] `tests/test_fabric_delivery_tracking.py`
- [x] `tests/test_fabric_commit_delivery.py`
- [x] `tests/test_fabric_commit_ingress.py`
- [x] `tests/test_fabric_ack_ingress.py`
- [x] `tests/test_fabric_quorum_runtime.py`
- [x] `tests/test_fabric_quorum_report.py`
- [x] `tests/test_fabric_report_writer.py`
- [x] `tests/test_fabric_runtime_bundle.py`
- [x] `tests/test_fabric_runtime_composer.py`
- [x] `tests/test_fabric_artifact_resolver.py`
- [x] `tests/test_fabric_runtime_helpers.py`
- [x] `tests/test_fabric_handshake_recorder_config.py`
- [x] `tests/test_detm_app_shim.py`
- [x] `tests/test_run_compat_facade.py`
- [x] `tests/test_entrypoint_facades.py`
- [x] `tests/test_ui_helper_facades.py`
- [x] `tests/test_no_detm_run_imports.py`
- [x] `tests/test_no_legacy_entrypoint_imports.py`
- [x] `tests/test_viz_facades.py`
- [x] `tests/test_napari_subscriber_path.py`
- [x] `tests/test_viz_streamer_multilevel.py`
- [x] `tests/test_watch_contract_writer.py`
- [x] `tests/test_pattern_memory.py`
- [x] `tests/test_refinement_mvp.py`

## Текущие пробелы (критично закрыть)

- [ ] Граница между библиотекой ядра и приложением остаётся неполной: `detm_app` выделен, а в `detm` всё ещё присутствуют compatibility facades (`detm/run/*`, `detm/cli.py`, `detm/ui/*`, `detm/viz/*`).
- [x] `LevelPolicy` доведён до полного runtime wiring для `microsteps/batch/publish`; multi-signal runtime adaptive contour расширен guardrails-ограничениями (`runtime_adaptive_guard_*`: `min/max`, `reject_unsafe`) и отражается в trace policy telemetry.
- [x] `refinement` есть как MVP (overflow/nonfinite/capacity detectors + ROI/sanitize correction); базовые temporal/memory-driven, learned/cross-level, operator-driven/cross-node, distributed/signed, cryptographic/consensus-grade и attestation/Byzantine-grade signals для ёмкости уровня добавлены.
- [x] Контур памяти паттернов расширен policy-driven scope-режимами (`pattern_reuse_scope`: `global|portable|strict`) с переносимостью между уровнями/режимами и тестовым покрытием.
- [x] Pruning по `error/deviation` реализован как MVP и покрыт расширенной абляционной валидацией на длинных сериях (`tests/test_pattern_memory.py`).
- [x] Канонический napari subscriber path реализован (`detm_app/napari_subscriber.py`; `detm_napari_viewer.py` как launcher-wrapper).
- [x] Production watch-contract и расширяющие тесты для watch/read-only проекций реализованы (`watch_contract.jsonl`, `outerfields/*.npz`, `tests/test_watch_contract_writer.py`).
- [x] Базовый набор runtime-профилей наблюдаемости и переключение профилей от adaptive signals реализованы (MVP).
- [x] Политика хранения `L0..Ln` покрывает ключевые L0-артефакты, runtime/fabric handshake отчёты, multi-level fallback профили и дополнительные runtime-отчёты (`commit_validation`, `fabric_quorum_report` history).
- [ ] `CommitPacket` и `realtime/audit` commit-writers разведены в node/fabric MVP (включая split-mode channel routing, `delivery_ack`, receipt retry/timeout, validator-set/reject policy), но нет production-доставки/репликации commit-логов (durable queue + distributed guarantees).
- [ ] Нет production transport-стека поверх `FabricEnvelope` (network MVP есть: TCP relay/adapter; есть local outbox + live backpressure + delivery receipt tracking, но нет end-to-end exactly-once/at-least-once guarantees, auth/encryption и distributed durable queue/coordination).
- [ ] Локальный validator (`commit_validation.json`) и distributed MVP wiring (`epoch/watermark gate`, shared artifact resolver, proof/trust acks, replay sampling policy) есть, но нет production replay-check/sampling и replicated validator-coordination между нодами.
- [ ] Нет production consensus fabric-координатора для `epoch/watermark`-согласования commit-ов между нодами (MVP есть: in-memory + shared file-state + replicated file-quorum + transport pre-consensus, но без replicated log/Byzantine-safe consensus).
- [ ] Нет production distributed validator handshake поверх `CommitChainManager` и `ProofAck/TrustAck`; network MVP работает через shared artifact resolver + `payload_inline` bridge + validator-set/quorum/retry/timeout/static-registry + transport pre-consensus primitives, но без full consensus/runtime membership.
- [ ] Нет end-to-end pipeline обучения реакций инвариантов (фаза 5 как code contour).
- [ ] Нет N-D runtime модели и межуровневой согласованной геометрии.

## План по этапам

### Этап A: Приложение и границы слоёв (`detm_app`)

- [x] Поднять `detm_app` shim-пакет с зеркальными импортами `bus/session/scheduler/coarsening` для совместимого migration path.
- [x] Перевести `cli`/`tk_runner` на app-layer импорты (`detm_app.*`) для `Session/Bus/Coarsening`.
- [x] Вынести `Session/Bus/Scheduler` из `detm/run` в `detm_app`.
- [x] Зафиксировать deprecation-policy и migration guide для `detm/run/*` до полного удаления facade.
- [x] Добавить CI-guard, запрещающий новые импорты `detm.run.*` вне compatibility слоя.
- [x] Добавить CI-guard, запрещающий новые импорты legacy entrypoints `detm.cli`/`detm.ui.*`/`detm.viz.*`.
- [ ] Оставить в `detm` только библиотечные контракты и вычислительное ядро.
- [x] Обеспечить совместимость CLI/UI без ломки текущего API.

Критерий готовности этапа A:
1. `detm` импортируется как чистая библиотека без app-orchestration допущений.
2. Все текущие сценарии запуска работают через `detm_app` адаптеры.

### Этап B: LevelPolicy как runtime-объект

- [x] Реализовать schema + runtime application `LevelPolicy` (MVP).
- [x] Довести связку microsteps/batch/publish до полного runtime wiring (не только commit/microstep).
- [x] Прозрачно логировать policy decisions в trace/readout (MVP trace fields).
- [x] Включить в `LevelPolicy` runtime-профили наблюдаемости (`allowed_event_types`, `detail_mode`) (MVP).
- [x] Добавить multi-signal runtime adaptive tuning (`runtime_adaptive_signal_event_types`, `runtime_adaptive_min_signals`, quality/cost thresholds, directional delta-mode, auto profile selection, anti-flap `runtime_adaptive_cooldown_ticks`, sampled/aggregated runtime-adaptive telemetry в trace/watch policy и/или override для `microsteps/batch/commit_stride`, `runtime_adaptive_hold_ticks`).
- [x] Добавить policy guardrails для runtime adaptive (`runtime_adaptive_guard_*`: `min/max`, `reject_unsafe`) с trace-видимостью и тестовым покрытием.

Критерий готовности этапа B:
1. Политика уровня изменяется данными, а не ad-hoc логикой кода.
2. Поведение тиков/публикации воспроизводимо и проверяемо тестами.
3. Профиль наблюдаемости переключается данными и отражается в trace/readout.

### Этап C: Refinement MVP

- [x] Добавить детекторы выхода за валидность уровня (MVP: `energy_overflow`, `state_nonfinite`).
- [x] Добавить базовый detector ёмкости уровня (MVP: `capacity_pressure` по доле overflow-клеток).
- [x] Вынести порог `capacity_pressure` в `LevelPolicy` (`refinement_capacity_overflow_ratio_threshold`).
- [x] Расширить `capacity_pressure` до policy-driven multi-signal gating (`overflow_ratio` + `overflow_mean`, `refinement_capacity_min_signals`).
- [x] Добавить temporal/memory-driven signal в `capacity_pressure` (`refinement_capacity_temporal_ratio_threshold`, `refinement_capacity_temporal_window`, `refinement_capacity_temporal_required_hits`).
- [x] Добавить learned/cross-level signals в `capacity_pressure` (`refinement_capacity_learned_hits_threshold`, `refinement_capacity_cross_level_window`, `refinement_capacity_cross_level_min_levels`).
- [x] Добавить operator-driven/cross-node signals в `capacity_pressure` (`refinement_capacity_operator_score_threshold`, `refinement_capacity_cross_node_min_signals`).
- [x] Добавить distributed/signed signals в `capacity_pressure` (`refinement_capacity_distributed_accepted_min`, `refinement_capacity_signed_acks_min`).
- [x] Добавить cryptographic/consensus-grade signals в `capacity_pressure` (`refinement_capacity_consensus_accepted_min`, `refinement_capacity_crypto_validator_coverage_min`).
- [x] Добавить attestation/Byzantine-grade signals в `capacity_pressure` (`refinement_capacity_attestation_validator_ids`, `refinement_capacity_attestation_min_coverage`, `refinement_capacity_byzantine_clean_min`).
- [x] Реализовать локальный refine ROI на `Ln-1` (MVP: локальная ROI-коррекция вокруг hotspot).
- [x] Реализовать `correction` и возврат в `Ln` в рамках одного commit-окна.

Критерий готовности этапа C:
1. Перегрузки уровня разрешаются локально без глобальной деградации.
2. Trace фиксирует факт refine и эффект correction.

### Этап D: Память паттернов и ускорение реакций

- [x] Ввести `PatternStore` (file-backed stub, версионирование).
- [x] Ввести `PatternCache` (LRU/TTL в RAM).
- [x] Подключить lookup/reuse паттерна до дорогого refine.
- [x] Ввести pruning по абляционным порогам `error/deviation` для `PatternStore/PatternCache`.
- [x] Добавить policy-driven scope для reuse (`pattern_reuse_scope`: `global|portable|strict`) и переносимость между уровнями/режимами.

Критерий готовности этапа D:
1. Повторяющиеся режимы реже уходят в refine.
2. Есть измеримое снижение стоимости тика на повторных паттернах.
3. Pruning воспроизводим политикой порогов и не ломает reuse-path.

### Этап E: Artifact-first наблюдаемость и napari migration

- [x] Зафиксировать production-контракт подписок (`OuterFields/metrics/events`) для L0 artifact-first path.
- [x] Разделить журнал на `System Trace` и `Watch Trace` (watchpoints как проекции поверх канонического журнала) (MVP).
- [x] Ввести `trace_ref`-дисциплину для любых проекций/уведомлений (MVP).
- [x] Зафиксировать policy хранения trace (`retention-window`, `compaction-budget`) (MVP).
- [x] Расширить L0 artifact storage policy на ключевые артефакты (`trace/watch_trace/watch_contract/outerfields/commits/commits_audit/history/invariants/commit_validation/fabric_acks/fabric_ack_envelopes/fabric_delivery_acks/fabric_dead_letters/fabric_quorum_report`).
- [x] Реализовать napari как read-only subscriber канонического transport-а.
- [x] Расширить napari read-only coverage на multi-level сценарии (`active_level` meta propagation + parser/tests).
- [ ] Оставить `Tk` как fallback/dev path до полной миграции.

Критерий готовности этапа E:
1. UI не требует прямого доступа к `DETMState`.
2. napari path функционально покрывает текущие ключевые сценарии наблюдения.
3. Любая watch-проекция/уведомление содержит валидный `trace_ref` и укладывается в policy хранения.

### Этап F: Обучение реакций (фаза 5 roadmap)

- [ ] Реализовать контур накопления correction/reaction как операторов.
- [ ] Ввести критерии переносимости операторов между режимами.
- [ ] Добавить anti-Goodhart readout для оценки качества обучения.

Критерий готовности этапа F:
1. Реакции устойчиво переиспользуются в новых, но близких режимах.
2. Улучшение не сводится к росту одной метрики.

### Этап G: N-мерность и node/fabric горизонт

- [ ] Обобщить `DETMState` на N-мерные поля.
- [ ] Согласовать межуровневые контракты для разных размерностей.
- [ ] Подготовить отдельный R&D контур `Node/Fabric/Protocol` поверх артефактных интерфейсов.
- [x] Зафиксировать `CommitPacket`-контракт и типы `StateCommit/BoundaryCommit/CoarsenedCommit/ProofCommit` (MVP schema + tests).
- [x] Поднять local validator-report (`chain/proof/watermark`) для commit-артефактов.
- [x] Ввести канонический `FabricEnvelope` (`type`, `channel`, `mode`, `payload_ref`) и topic-based routing для node/fabric сообщений (MVP: `InMemoryFabricBus`).
- [x] Ввести `CommitChainManager` (`tail`, `parent_ref`, `sequence/verify`) как runtime-слой поверх `CommitPacket` (MVP).
- [ ] Ввести `ProofAck/TrustAck` контур (подпись, проверка, подтверждение commit-цепочки) для validator/fabric (local + distributed MVP wiring реализованы: validator-set/quorum/retry/timeout, shared artifact resolver, epoch/watermark gate, transport pre-consensus; production-consensus в работе).
- [ ] Ввести production fabric-контур согласования `epoch/watermark` по commit boundary (MVP реализован: in-memory + shared file-state + replicated file-quorum + transport pre-consensus, без hard-barrier внутри шага ноды).
- [x] Развести межнодовый транспорт на режимы `realtime` (thin commit) и `audit` (thick commit) на уровне node-to-node fabric (MVP: mode-aware `commit/ack` channels + runtime/CLI wiring).
- [ ] Подготовить R&D-дизайн `local-first + validation-sync` как pre-distributed трек для `Node/Fabric`.

Критерий готовности этапа G:
1. Базовые контуры работают вне 2D-only предположений.
2. Node/Fabric не ломает канон L0/runtime контрактов.
3. `CommitPacket` и epoch/watermark-согласование обеспечивают воспроизводимый межнодовый replay/валидацию.
4. `local-first + validation-sync` описан как отдельный экспериментальный протокол без влияния на канон.

## Ближайшие 5 шагов (приоритет)

- [x] 1. Поднять минимальный `LevelPolicy` в коде (`schema + runtime usage + trace fields + observability profiles`).
- [x] 2. Выделить `detm_app` и мигрировать туда `Session/Bus/Scheduler`.
- [x] 3. Сделать `refinement` MVP (детектор + локальный ROI + correction).
- [x] 4. Добавить `PatternStore` stub + `PatternCache` LRU + lookup до refine + pruning (`error/deviation`).
- [x] 5. Закрепить artifact-first UI path: довести storage policy для дополнительных runtime-отчётов `L1..Ln`.

## Псевдоцели (учитывать, но не подменять KPI)

- [x] Исследовать применимость релятивистской геометрии/инвариантов как слоя управления нейросетями.
- [x] Использовать физический мотив структурообразования (в т.ч. кристаллические паттерны) как источник гипотез.
- [x] Двигаться к агенту навыков (переносимых операторов), а не к агенту контекста.
- [x] Не оценивать прогресс этими пунктами как критериями готовности этапов A-G.

## Что взято из `D:\github\game` как полезный паттерн

- [x] Формат roadmap как operational control panel (`Checkup -> Реализовано -> Пробелы -> Этапы -> Ближайшие шаги`).
- [x] Чеклистная дисциплина `[x]/[ ]` для сохранения контекста между сессиями.
- [x] Критерии готовности на каждый этап вместо абстрактных намерений.
- [x] Разделение факта реализации и целевого дизайна в одном документе.

### Кандидаты на перенос в DETM (из просмотренных `game` docs)

- [x] Разделить trace на `System Trace` и `Watch Trace` (операторские/исследовательские watchpoints поверх канонического журнала).
- [x] Добавить `trace_ref`-дисциплину: любая проекция/уведомление должна ссылаться на committed артефакт.
- [x] Зафиксировать policy хранения по уровням (`L0..Ln`) с retention-окнами и compaction-budget.
- [x] Довести pruning паттернов до runtime-контура (`PatternStore/PatternCache`) через абляционные пороги `error/deviation`.
- [x] Ввести явные runtime-профили наблюдаемости (`allowed_event_types`, `detail_mode`) для anti-noise диагностики.
- [ ] Рассмотреть local-first + validation-sync контур как отдельный трек для будущего distributed/node-fabric этапа.

Статус на 2026-02-10: первые 5 кандидатов приняты в целевую архитектуру и разнесены по этапам B/D/E; `local-first + validation-sync` оставлен как отдельный R&D трек этапа G.

### Кандидаты на перенос в DETM (из кода `D:\github\game\references\old_repo\lib`)

- [x] Паттерн transport-envelope (`type/listener/data`) из `network/ledger/AJWSPackageRequest.py` принят как основа `FabricEnvelope` (`type/channel/mode/payload_ref`).
- [x] Паттерн commit-цепочки (`tail -> parent`) из `ledger/package/PackageManager.py` принят для `CommitChainManager` node/fabric уровня.
- [x] Паттерн typed codec (`PackageJSONEncoder/PackageJSONDecoder`) принят для отдельного `CommitCodec` и симметричной сериализации/десериализации payload.
- [x] Паттерн отдельного trust-пакета (`ledger/package/PackageTrust.py`) принят как основа `ProofAck/TrustAck` в validator/fabric контуре.
- [x] Паттерн event-pubsub из `publisher/Publisher.py` принят как минимальная модель topic-based dispatch в fabric.
- [x] Паттерн декомпозиции по классам (контракты/менеджеры/адаптеры) принят как стиль реализации fabric-слоя DETM.
- [x] Зафиксировано ограничение: `scheduler/*` из `old_repo` не переносится as-is (много заглушек, недетерминированный и незавершённый контур).

Статус на 2026-02-10: паттерны зафиксированы в архитектурных документах и разнесены в задачи этапа G; прямой кодовый перенос из `old_repo/lib` не планируется.

## Основной контрольный вопрос

> Приближает ли конкретное изменение DETM к целевой архитектуре,
> или закрепляет переходный путь как постоянный?
