# ROADMAP (human)

Обновлено: 2026-02-14

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
- [x] Тестовый snapshot зелёный: `pytest -q -> 348 passed`
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
- [ ] Нет code-contour фазы F (reaction operators + transferability + anti-Goodhart)
- [ ] Нет N-D runtime модели и межуровневой геометрии
- [ ] Нет отдельной formal спецификации `local-first + validation-sync` как R&D трека
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

- [ ] F-01: накопление reaction/correction операторов
- [ ] F-02: переносимость операторов (`hold_rate`, `operator_reuse`, `transferability`)
- [ ] F-03: anti-Goodhart readout + `goodhart_flag`

### Этап G-ND (N-мерность)

- [ ] G-ND-01: `DETMState` `(H,W)` -> `shape[N]` (backward compatible)
- [ ] G-ND-02: N-D контракты `serialization/refinement/outerfields`
- [ ] G-ND-03: UI projection adapters для совместимости napari/readout consumers

### Этап G-R&D (local-first)

- [ ] G-RND-01: отдельная спецификация `local-first + validation-sync` (prod-scope vs R&D-scope)

### Этап RT-MNT (`detm/runtime` structural refactor)

- [x] RT-MNT-01: декомпозиция `refinement/apply.py` (`maybe_apply_refinement` pipeline split)
- [x] RT-MNT-02: разделение `level_policy/*` на model/normalize/decision
- [x] RT-MNT-03: декомпозиция `fabric/runtime_composer` + handshake normalize path
- [x] RT-MNT-04: закрыть schema migration path в `detm/runtime/serialization/*`

### Этап PUB (public packaging, non-blocking)

- [ ] PUB-01: добавить 3-5 demo assets (`docs/book/assets`) и встроить их в `README.md`
- [ ] PUB-02: зафиксировать 2-3 каноничных визуальных пресета с командами воспроизведения
- [ ] PUB-03: сделать one-page описание проекта (RU/EN)
- [ ] QLT-01: усилить docstrings/type hints для ключевых runtime API
- [ ] DAGM-01: оформить RFC по отдельному DAGM general-graph runtime треку (без срыва текущего фокуса)

## Следующие 5 шагов (приоритет)

- [ ] 1. Закрыть `F-01` (контур reaction/correction operators в коде)
- [ ] 2. Закрыть `G-ND-01` (эволюция `DETMState` к `shape[N]`)
- [ ] 3. Закрыть `F-02` (переносимость операторов)
- [ ] 4. Закрыть `F-03` (anti-Goodhart readout + `goodhart_flag`)
- [ ] 5. Закрыть `G-ND-02` (N-D контракты serialization/refinement/outerfields)

## Imported from game (кратко)

Уже реализовано в DETM:

- [x] `System Trace`/`Watch Trace` + `trace_ref`
- [x] Artifact-first watch contract (`OuterFieldsRef` linkage)
- [x] Pattern pruning/memory runtime contour
- [x] Commit/envelope/quorum decomposition style

Остаётся как pending/R&D:

- [ ] `local-first + validation-sync` как отдельный протокол
- [ ] Полный packet-level parity по `commit/correction/influence`
- [ ] Runtime anti-Goodhart контур (пока преимущественно docs-level)

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
