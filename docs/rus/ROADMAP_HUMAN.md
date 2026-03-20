# ROADMAP (human)

Обновлено: 2026-03-20

> Этот файл — человеческая версия roadmap в старом формате (как в `D:\github\game\ROADMAP.md`).
> Детальная инженерная спецификация с PM-полями: `docs/rus/ROADMAP.md`.
> Статусы задач обновляются в первую очередь в `docs/rus/ROADMAP.md` (source-of-truth), этот файл — читабельная проекция.

## Цель

Зафиксировать текущее состояние DETM и понятный план работ без перегруза деталями,
чтобы между сессиями не терялся контекст: что уже сделано, что переходное,
и что закрывать в первую очередь.

## Легенда

- `[x]` сделано
- `[ ]` в работе или запланировано

## Checkup (снимок состояния)

- [x] `detm` очищен до library-core, app-layer вынесен в `detm_app`
- [x] Канонический runtime API L0 стабилен (`reset/step/digest/serialize/deserialize`)
- [x] Реализованы `LevelPolicy`, `refinement` MVP, `PatternStore/PatternCache` + pruning
- [x] Артефактный контур наблюдаемости закреплён (`System Trace` + `Watch Trace` + `trace_ref`)
- [x] Napari read-only path канонизирован, есть phase-profiler старта
- [x] Fabric runtime сведен в единый namespace `detm/runtime/fabric/*`
- [x] Есть network MVP: TCP relay/transport, TLS/HMAC, dedup, backpressure, delivery receipts
- [x] Есть epoch/watermark + pre-consensus MVP + quorum/reporting
- [x] Архитектурные docs/cards синхронизированы с текущим layout (`detm_app/runtime/*`, launcher `main.py`, `detm/runtime/fabric/*`)
- [x] Добавлен local-first analytics read-model: post-run ingest в `analytics.sqlite` + structured exports в `analytics/*`
- [x] Тестовый snapshot зелёный: `pytest -q -> 425 passed`
- [x] Веточная политика зафиксирована: разработка через `dev/main`, релизы через `main` (`docs/BRANCHING.md`)

## Зафиксированные архитектурные решения

- [x] L0 runtime UI-агностичен
- [x] Внешние потребители читают артефакты, а не live-state
- [x] `OuterFields`/подписки — основной интерфейс наблюдаемости
- [x] `System Trace` канонический, `Watch Trace` проекционный
- [x] Любая внешняя проекция обязана нести `trace_ref`
- [x] Любая инженерная задача оценивается по критерию: приближает к target-архитектуре или закрепляет transition
- [x] Целевой baseline для fabric: `at-least-once + idempotency`
- [x] Базовый deployment-профиль hardening: `single-host multi-process`

## Что уже реализовано (крупно)

- [x] Этап A: граница `detm`/`detm_app` + migration/CI guards
- [x] Этап B: data-driven `LevelPolicy` + adaptive runtime tuning
- [x] Этап C: `refinement` MVP (detectors + ROI/correction)
- [x] Этап D: память паттернов и pruning
- [x] Этап E: artifact-first наблюдаемость + napari migration track

## Текущие пробелы (критично закрыть)

- [x] Закрыт production-baseline delivery guarantees (`at-least-once + idempotency`) end-to-end
- [x] Закрыт production-grade durable coordination для outbox/tracking/receipts
- [x] Закрыт baseline replicated validator coordination + replay policy tiers (`G-FAB-03`)
- [x] Закрыт production hardening для `epoch/watermark` consensus path (`G-FAB-04`)
- [x] Закрыт production profile distributed validator handshake поверх `ProofAck/TrustAck` (`G-FAB-05`)
- [x] Есть baseline code-contour фазы F (reaction operators + transferability + anti-Goodhart)
- [ ] Нет N-D runtime модели и межуровневой геометрии
- [ ] Нет отдельной formal спецификации `local-first + validation-sync` как R&D трека
- [ ] Нет follow-up этапа для оптимизации шумного `outerfields` хранения поверх уже добавленного analytics read-model
- [x] Закрыт app-layer maintenance debt (`config -> runner` decoupling, viewer adapter registry, shared batch service)
- [ ] Остался P1 runtime/app structural debt (крупные orchestration-модули: `detm/runtime/fabric/tcp_transport/transport.py`, `detm_app/runtime/subscribers/fabric/*`)

## План по этапам

### Этап A-E (baseline/maintenance)

- [x] A: приложение и границы слоёв
- [x] B: `LevelPolicy` как runtime-объект
- [x] C: `refinement` MVP
- [x] D: память паттернов
- [x] E: artifact-first наблюдаемость + napari read-only
- [x] E-MNT: завершить napari-only cutover и перенести манипуляции Tk в `napari --interactive` (interactive + batch)
- [x] E-MNT-02: вынести `UiRunSettings` в отдельный config-model слой
- [x] E-MNT-03: adapter-registry для viewer в `detm_app.runner.shell`
- [x] E-MNT-04: единый batch service для napari/tk UI
- [x] E-MNT-05: декомпозиция крупных app-layer модулей (`runner/headless/*`, `napari/interactive/*`, `tk/runner/*`)
- [x] Pre-tag cleanup migration-артефактов: удалён `detm.py` (каноничный вход только `main.py`), переписаны boundary checks в устойчивом AST-формате, убраны дубли import-guard тестов

### Этап FAB (production baseline)

- [x] G-FAB-01: delivery guarantees (`at-least-once + idempotency`)
- [x] G-FAB-02: durable queue/coordination baseline
- [x] G-FAB-03: validator coordination + replay policy tiers
- [x] G-FAB-04: epoch/watermark consensus hardening
- [x] G-FAB-05: distributed validator handshake production profile

### Этап F (обучение реакций)

- [x] F-01: накопление reaction/correction операторов
- [x] F-02: переносимость операторов (`hold_rate`, `operator_reuse`, `transferability`)
- [x] F-03: anti-Goodhart readout + `goodhart_flag`

Примечание (2026-03-20): baseline F-контур уже закрыт в коде. В runtime есть явный operator-contract в refinement events, bounded history/persistence и отдельный artifact-first поток `operator_decisions.jsonl`; portability-панель (`hold_rate/operator_reuse/transferability`) измерима через формальный acceptance-gate; anti-Goodhart контур rule-based и policy-driven, экспортируется в `watch_trace/watch_contract`, а exploration-horizon (`exploration_horizon_ticks`, `horizon_break_reason`, `recovery_cost_ticks`) уже живёт в runtime/watch/readout и связан с anti-Goodhart/runtime-adaptive слоем. Это закрывает baseline phase-F code contour, но не обещает ML-heavy learning pipeline или более широкий auto-tuning beyond current bounded contract.

### Этап G-ND (N-мерность)

- [x] G-ND-01: `DETMState` `(H,W)` -> `shape[N]` (backward compatible)
- [x] G-ND-02: N-D контракты `serialization/refinement/outerfields`
- [x] G-ND-03: UI projection adapters для совместимости napari/readout consumers

Примечание (2026-03-20): baseline N-D migration/runtime contour закрыт в bounded форме. `DETMConfig` получил канонический `shape[N]`, `width/height` остались backward-compatible alias последних двух осей, state serialization держит N-D shape, а публичный `reset(...)` создаёт N-D state. Дальше N-D контракт был доведён через readout/detection/runtime slices: `digest(...)` и readout используют каноническую 2D-проекцию по trailing axes, `NumpyBackend` и `TorchBackend` умеют plane-wise evolution, influence-path обобщён на leading-axis broadcast, а refinement выполняется plane-wise с отдельными `plane_index` events. Это закрывает текущий bounded N-D runtime/serialization/refinement/outerfields слой, но не объявляет richer cross-plane semantics или новую “настоящую” N-D геометрию финальной архитектурой.
Примечание (2026-03-20, закрытие `G-ND-03`): adapter-layer для текущих watch/readout consumers доведён до bounded logical completion. `watch_trace` и `watch_contract` явно несут `projection` metadata о том, как N-D state был свёрнут в каноническую 2D плоскость (`source_shape -> projected_shape`, collapsed axes/count, reduction mode), а `outerfields` для N-D строятся из той же канонической проекции. Эта же metadata дошла до UI learning/readout слоя: snapshot и status panel показывают пользователю, что он смотрит на projected plane, а не на “обычную” 2D сцену. Napari interactive получил plane selector для N-D просмотра (`mean` или конкретная плоскость по leading axes) только для visual inspection, а graph/readout adapter в napari развели честно: графики по-прежнему строятся из canonical `learning_snapshot`, а plane-local визуальная информация добавляется только как отдельные `visual_energy_*` series и явная маркировка `telemetry=<canonical projection>` / `view=<selected plane>` в status. Embedded Tk viz panel тоже больше не 2D-only: он читает ту же каноническую projection для N-D state и показывает краткий `proj=` suffix в status. Это закрывает именно compatibility/adapter слой для текущих consumers, но не объявляет full N-D UI: richer cross-plane presentation, multi-plane sync и смена канонического watch/readout projection contract по-прежнему вне этого этапа.

### Этап G-R&D (local-first)

- [ ] G-RND-01: отдельная спецификация `local-first + validation-sync` (prod-scope vs R&D-scope)

### Этап RT-MNT (`detm/runtime` structural refactor)

- [x] RT-MNT-01: декомпозиция `refinement/apply.py` (`maybe_apply_refinement` pipeline split)
- [x] RT-MNT-02: разделение `level_policy/*` на model/normalize/decision
- [x] RT-MNT-03: декомпозиция `fabric/runtime_composer` + handshake normalize path
- [x] RT-MNT-04: закрыть schema migration path в `detm/runtime/serialization/*`

### Этап ANL (analytics read-model)

- [x] ANL-01: local-first SQLite read-model + structured run packs

Примечание (2026-03-20): в app-layer добавлен post-run analytics контур на `sqlite3`, не меняющий runtime write path. Completed run теперь можно ingest-ить в `analytics.sqlite`, а рядом строятся derived exports `analytics/run_summary.json`, `analytics/event_windows.jsonl`, `analytics/decision_windows.jsonl`, `analytics/outerfields_index.jsonl`. Raw artifact-first слой остаётся source-of-truth; SQLite хранит только summaries/refs/meta без dense arrays. Реальный ingest на `runs/out/ui_run` показывает, что слой пригоден для chain/trace/decision analysis и честно маркирует неполный artifact-set как `partial`, если `watch_contract` ссылается на отсутствующие `outerfields` файлы. Это закрывает именно read-model/analytics baseline, но не оптимизирует сам raw outerfields storage format и не вводит live DB writer.

### Этап MSC (multiscale bridge catalog, observe-only baseline)

- [x] MSC-01: bounded observe-only baseline для multiscale/Redis трека

Примечание (2026-03-20): в `DETMConfig` добавлен `multiscale_catalog` block, а `pattern_memory` расширен local ring buffer и bridge-record shaped observe-only catalog state. На `step` events теперь можно писать derived artifacts `multiscale_candidates.jsonl`, `scale_tension.jsonl`, `operator_catalog_hits.jsonl`, а analytics ingest индексирует их в `analytics.sqlite`. Это ещё не runtime acceleration и не full Redis bridge runtime: `hint/jump`, live Redis transport, trajectory DB с full forward/reverse bodies и particle/macronode semantics остаются следующим отдельным этапом.

### Этап PUB (public packaging, non-blocking)

- [ ] PUB-01: добавить 3-5 demo assets (`docs/media`) и встроить их в `README.md`
- [ ] PUB-02: зафиксировать 2-3 каноничных визуальных пресета с командами воспроизведения
- [ ] PUB-03: сделать one-page описание проекта (RU/EN)
- [ ] QLT-01: усилить docstrings/type hints для ключевых runtime API
- [ ] DAGM-01: оформить RFC по отдельному DAGM general-graph runtime треку (без срыва текущего фокуса)

## Следующие 5 шагов (приоритет)

- [ ] 1. Описать `G-RND-01` как отдельный `local-first + validation-sync` R&D трек
- [ ] 2. Спроектировать follow-up к `MSC-01`: Redis hot transport + trajectory store DB (`BridgeRecordSource`, verification, forward/reverse bodies) без premature jump semantics
- [ ] 3. Спроектировать follow-up к `ANL-01`: sharded/deduplicated policy для raw `outerfields` и bounded retention для long runs
- [ ] 4. Закрыть `PUB-01` (demo assets в `docs/media` и README)
- [ ] 5. Закрыть `PUB-02` или `PUB-03` в зависимости от того, что сильнее помогает external readability текущего baseline

## Imported from game (кратко)

Уже реализовано в DETM:

- [x] `System Trace`/`Watch Trace` + `trace_ref`
- [x] Artifact-first watch contract (`OuterFieldsRef` linkage)
- [x] Pattern pruning/memory runtime contour
- [x] Commit/envelope/quorum decomposition style

Остаётся как pending/R&D:

- [ ] `local-first + validation-sync` как отдельный протокол
- [ ] Полный packet-level parity по `commit/correction/influence`
- [ ] Runtime anti-Goodhart контур (code-level baseline есть, нужен полный DoD)

## Weekly checkpoints

- [ ] 2026-02-16 — структура и P0 gate review
- [ ] 2026-02-23 — delivery+durability gate (`G-FAB-01/02`)
- [ ] 2026-03-02 — validator/epoch gate (`G-FAB-03/04`)
- [ ] 2026-03-09 — handshake gate + старт F (`G-FAB-05`, `F-01`)
- [ ] 2026-03-16 — F metrics/anti-Goodhart + N-D kickoff
- [ ] 2026-03-23 — app/runtime refactor gate (`E-MNT-02..05`, `RT-MNT-01..04`)

## Основной контрольный вопрос

> Приближает ли конкретное изменение DETM к целевой архитектуре,
> или закрепляет переходный путь как постоянный?
