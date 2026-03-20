# ROADMAP V2 — DETM

Обновлено: 2026-03-20

Короткая версия для чтения: `docs/rus/ROADMAP_HUMAN.md`.
Source-of-truth по статусам и зависимостям задач: `docs/rus/ROADMAP.md`.

## Scope

Этот документ фиксирует:

- фактическое состояние DETM в текущем workspace (`as-is`);
- целевую архитектуру (`to-be`) и путь миграции;
- исполнимый PM+engineering контур для открытых задач;
- критерий контроля: изменение приближает к target-архитектуре или закрепляет transition как финал.

Документ заменяет "общий чеклист" детализированным форматом `ROADMAP Item v2`.

## Легенда

- `status`: `todo | in_progress | done | blocked`
- `priority`: `P0 | P1 | P2`
- `owner_role`: `runtime | fabric | docs | qa | infra`

## North Star и инварианты

1. `detm` — библиотечное ядро; orchestration/UI живут в `detm_app`.
2. `L0 runtime` остаётся UI-агностичным и single-writer.
3. Внешний доступ только artifact-first (`OuterFields/metrics/events/trace_ref`).
4. `System Trace` канонический; `Watch Trace` — проекция с обязательным `trace_ref`.
5. Любая работа оценивается по критерию: приближает ли она проект к target-архитектуре.
6. Целевая delivery-гарантия fabric baseline: `at-least-once + idempotency`.
7. Базовый deployment-профиль для production-hardening: `single-host multi-process`.

## ROADMAP Item v2 (шаблон)

Каждый open-item в этом документе обязан содержать поля:

- `id`
- `status`
- `priority`
- `owner_role`
- `target_date`
- `depends_on`
- `scope_in`
- `scope_out`
- `deliverables`
- `api_contract_changes`
- `tests_required`
- `readout_artifacts`
- `risks`
- `dod`

## Status Snapshot

### Канон и архитектура

- Зафиксирован канон DETM и north star (`.codex/PROMT.md`, `docs/rus/30_architecture/target_architecture_synthesis.md`).
- Граница `detm`/`detm_app` очищена; legacy entrypoints удалены.
- `System Trace`/`Watch Trace` и `watch_contract` в production-контуре.
- Веточный контур разработки зафиксирован: активная разработка идёт через `dev/main`, `main` используется как release-ветка (`docs/BRANCHING.md`).

### Runtime/Fabric

- `CommitPacket`, `FabricEnvelope`, `CommitChainManager`, `ProofAck/TrustAck` и handshake runtime вынесены в `detm/runtime/fabric/*`.
- Есть transport/network MVP (`InMemoryFabricBus`, `TcpFabricTransport` + TLS/HMAC + dedup + backpressure).
- Есть epoch/watermark и pre-consensus MVP, delivery outbox, receipt tracking, quorum reports.

### Analytics/Artifacts

- В app-layer добавлен local-first SQLite read-model для post-run ingest: `detm_app/storage/analytics_db`.
- Для завершённого run-а теперь могут строиться derived analytics artifacts: `analytics.sqlite`, `analytics/run_summary.json`, `analytics/event_windows.jsonl`, `analytics/decision_windows.jsonl`, `analytics/outerfields_index.jsonl`.
- Канон не изменён: raw artifact-first слой (`trace/watch/contract/outerfields/state`) остаётся source-of-truth, а SQLite хранит summaries/refs/meta без dense array blobs.

### Тестовый срез

- Локальный snapshot (2026-03-20): `pytest -q -> 425 passed`.
- Fabric-focused срез в roadmap и status snapshots уже зафиксирован (`docs/rus/90_notes/status_snapshot_2026-02-12_fabric_and_napari.md`, `docs/rus/90_notes/status_snapshot_2026-02-13_napari_phase_profiler.md`).

## Workstreams

## WS-A..E — Baseline/Maintenance (закрытые этапы)

Этапы A–E считаются закрытыми как baseline. Открыты только maintenance-пункты, не блокирующие P0 fabric:

- `E-MNT-01`: финализировать napari-only cutover в canonical entrypoints/docs и закрыть regression/smoke.
- `E-MNT-02`: decouple `UiRunSettings` contract от `runner`-модуля в отдельный config-model слой.
- `E-MNT-03`: viewer adapter registry для `detm_app.runner.shell` вместо прямых imports viewer-реализаций.
- `E-MNT-04`: вынести общий batch-orchestration service из UI frontends.
- `E-MNT-05`: декомпозиция крупных app-layer модулей (`runner/headless/*`, `napari/interactive/*`, `tk/runner/*`).

## WS-FAB — Fabric Production Baseline (P0)

Цель: довести текущий fabric MVP до production-baseline в пределах `single-host multi-process`, без завышенных обещаний exactly-once.

Состав:

- `G-FAB-01` Delivery guarantees (`at-least-once + idempotency`)
- `G-FAB-02` Durable queue/coordination baseline
- `G-FAB-03` Validator coordination + replay policy tiers
- `G-FAB-04` Epoch/watermark consensus hardening
- `G-FAB-05` Distributed validator handshake production profile

## WS-F — Learning Code Contour

Цель: перевести phase F из doc-only в runtime/code контур.

Состав:

- `F-01` Контур накопления reaction/correction операторов
- `F-02` Переносимость операторов (`hold_rate`, `operator_reuse`, `transferability`)
- `F-03` Anti-Goodhart readout + `goodhart_flag`

## WS-G-ND — N-D Runtime Migration

Цель: убрать 2D-only предпосылки из state/runtime контрактов.

Состав:

- `G-ND-01` Эволюция `DETMState`: `(H,W)` -> `shape[N]` (backward compatible)
- `G-ND-02` N-D контракты serialization/refinement/outerfields
- `G-ND-03` UI-compatible projection adapters (napari/readout consumers)

## WS-G-RND — Local-first + Validation-sync

Цель: оформить отдельный R&D протокол поверх текущих `CommitPacket/FabricEnvelope/epoch/watermark` контрактов, без влияния на канон.

Состав:

- `G-RND-01` Спецификация local-first + validation-sync (boundaries, prod-scope vs R&D-scope).

## WS-RT-MNT — Runtime Refactoring Completion (`detm/runtime`)

Цель: закрыть незавершенный structural-refactor runtime после переноса в namespace-пакеты и снизить риск регрессий при F/N-D треках.

Состав:

- `RT-MNT-01` Декомпозиция `refinement/apply.py` (`maybe_apply_refinement`) на pipeline-модули.
- `RT-MNT-02` Разделение `level_policy/*` на model/normalize/decision слои.
- `RT-MNT-03` Разделение `fabric/runtime_composer/composer.py` и handshake-normalize path на более мелкие сервисы.
- `RT-MNT-04` Завершение schema migration контура в `serialization/*` (убрать placeholder `migrate_state`).

## WS-PUB — Public Research Packaging (non-blocking)

Цель: усилить публичную читаемость и воспроизводимость проекта без изменения канона L0/runtime.

Состав:

- `PUB-01` Demo assets в `docs/media` (визуальный baseline для README).
- `PUB-02` Каноничный пакет визуальных пресетов.
- `PUB-03` One-page overview (RU/EN) для быстрого входа.
- `QLT-01` Code-level docstrings/type hints для ключевых runtime-модулей.
- `DAGM-01` RFC по general-graph runtime треку (DAGM beyond lattice).

## WS-ANL — Artifact Analytics Read-Model

Цель: добавить local-first post-run analytics слой поверх текущих artifact-first run outputs без перевода runtime на direct DB writes.

Состав:

- `ANL-01` SQLite read-model + structured run packs
- `MSC-01` Observe-only multiscale bridge catalog baseline

## PM Registry (open items)

### ANL-01 — SQLite read-model + structured run packs

- `id`: `ANL-01`
- `status`: `done`
- `priority`: `P1`
- `owner_role`: `runtime`
- `target_date`: `2026-03-20`
- `depends_on`: `[]`
- `scope_in`: добавить app-layer storage/analytics контур с post-run ingest в `analytics.sqlite`, derived exports (`run_summary.json`, `event_windows.jsonl`, `decision_windows.jsonl`, `outerfields_index.jsonl`), Python API (`ingest_run`, `summarize_run`, `open_run_db`) и headless CLI (`main.py headless analytics ...`).
- `scope_out`: direct DB writes из runtime/subscribers, Postgres/Redis, live tailing/dashboards, dense arrays/BLOB storage в БД, изменение raw artifact writer semantics.
- `deliverables`: `detm_app/storage/analytics_db/*`, headless analytics CLI, tests на ingest/idempotency/partial mode/query path, structured exports рядом с run-dir.
- `api_contract_changes`: новый app-layer analytics API и CLI; existing runtime contracts не меняются.
- `tests_required`: ingest full-run, re-ingest idempotency, partial ingest, `watch_trace_enabled=false`, zero-event run, CLI smoke/query tests.
- `readout_artifacts`: `analytics.sqlite`, `analytics/run_summary.json`, `analytics/event_windows.jsonl`, `analytics/decision_windows.jsonl`, `analytics/outerfields_index.jsonl`.
- `risks`: принять read-model как замену raw artifacts; раздувать run summary тысячами per-tick warnings; путать partial run artifacts с ingest failures.
- `dod`: completed run можно аналитически прочитать через SQLite/derived JSONL без ручного разбора raw jsonl; SQLite содержит summaries/refs/meta, а не dense arrays; ingest идемпотентен и raw artifact-first канон сохранён.
- `readout` (2026-03-20): добавлен `detm_app/storage/analytics_db` на stdlib `sqlite3` с таблицами `runs`, `tick_summary`, `operator_panel`, `artifact_refs`, `run_issues`; headless CLI расширен под `analytics ingest|summarize|query`; structured exports пишутся в `run_dir/analytics/*`; ingest работает как post-run step и не меняет runtime/subscriber write path. Реальный ingest на `runs/out/ui_run` подтверждает `2668` ticks / `21` eventful ticks / `21` decision ticks и корректно маркирует run как `partial`, если `watch_contract` ссылается на отсутствующие `outerfields` artifacts. Summary warnings агрегируются по code-level, чтобы long-run readout не раздувался тысячами строк.

### MSC-01 — Observe-only multiscale bridge catalog baseline

- `id`: `MSC-01`
- `status`: `done`
- `priority`: `P1`
- `owner_role`: `runtime`
- `target_date`: `2026-03-20`
- `depends_on`: `[ANL-01]`
- `scope_in`: добавить bounded `observe-only` baseline для multiscale/Redis трека без изменения canonical runtime math: новый `multiscale_catalog` config block, bridge-oriented record shape (`window_signature/interface_signature/horizon/forward/reverse placeholder/validity/db_refs`), local ring buffer в `pattern_memory`, derived artifacts (`multiscale_candidates.jsonl`, `scale_tension.jsonl`, `operator_catalog_hits.jsonl`) и индексирование этих artifacts в `analytics.sqlite`.
- `scope_out`: runtime `jump` substitution, policy-driven `hint` execution, обязательный live Redis dependency, хранение dense grids в Redis, trajectory store DB для full forward/reverse bodies, particle semantics как final architecture.
- `deliverables`: `MultiscaleCatalogConfig`, bridge-record scaffolding в `detm.runtime.pattern_memory`, observe-only subscriber/writer, tests на config roundtrip/ring-buffer/graceful degradation/analytics ingest.
- `api_contract_changes`: расширение `DETMConfig` новым nested block `multiscale_catalog`; новые derived artifact files рядом с run-dir.
- `tests_required`: config roundtrip, observe-only artifact emission, graceful degradation при `redis_url` без redis client, analytics ingest/indexing.
- `readout_artifacts`: `multiscale_candidates.jsonl`, `scale_tension.jsonl`, `operator_catalog_hits.jsonl`, `analytics.sqlite` artifact refs.
- `risks`: выдать observe-only baseline за готовый `Ln <-> Ln+1` bridge runtime; начать считать Redis source-of-truth; перенести в Redis dense state вместо signatures/operators/refs.
- `dod`: runtime остаётся canonical single-writer; multiscale слой сидит поверх `step` events; ring buffer bounded; отсутствие redis dependency не роняет run; analytics видит новые artifacts.
- `readout` (2026-03-20): добавлен `multiscale_catalog` config block (`observe|hint|jump`, Redis URL, ring window, patch/interface quantization, support/confidence thresholds); `PatternMemoryRuntime` расширен bounded local multiscale ring buffer и `BridgeRecord`-shaped observe-only catalog state; app-layer subscriber пишет `multiscale_candidates.jsonl`, `scale_tension.jsonl`, `operator_catalog_hits.jsonl`; analytics ingest индексирует эти files как derived artifacts. Это сознательно не runtime acceleration: `hint/jump`, trajectory DB, reverse refine bodies и full Redis transport semantics остаются отдельным следующим этапом.

### E-MNT-01 — Napari-only cutover в canonical entrypoints/docs

- `id`: `E-MNT-01`
- `status`: `done`
- `priority`: `P1`
- `owner_role`: `docs`
- `target_date`: `2026-02-13`
- `depends_on`: `[]`
- `scope_in`: удалить `Tk` из canonical entrypoints/shell role matrix, синхронизировать roadmap/human/readme на napari-only путь и перенести runtime-манипуляции UI в napari interactive mode.
- `scope_out`: удаление/рефактор внутренних `detm_app.ui.tk.*` модулей.
- `deliverables`: обновлённые `main.py`/`detm_app.runner.shell` routing-контракты, napari interactive controls (`detm_app.ui.napari.interactive`), regression tests, синхронизированные roadmap документы.
- `api_contract_changes`: нет.
- `tests_required`: entrypoint routing + shell orchestration + import-guard tests для napari-only матрицы; napari interactive routing/helpers tests.
- `readout_artifacts`: `docs/rus/ROADMAP.md`, `docs/rus/ROADMAP_HUMAN.md`, target pytest logs (`tests/test_main_entrypoint_routing.py`, `tests/test_shell_orchestrate.py`, `tests/test_entrypoints_use_detm_app.py`, `tests/test_napari_lab_launcher.py`, `tests/test_napari_interactive_controls.py`).
- `risks`: частичный перенос (код без doc-синхронизации или наоборот).
- `dod`: canonical `main.py`/`shell` не содержат `runner=ui`/`viewer=tk`; roadmap и тесты подтверждают napari-only execution path.
- `readout` (2026-02-13): `main.py` переведён на napari-first/napari-only UI entry; `detm_app.runner.shell` ограничен `runner=headless`, `viewer=none|napari`; добавлен `main.py napari --interactive` с in-process манипуляциями (run/step/reset, influence/config/recording controls + quiver overlay) и batch-режимом (Run/Stop batch, queue/log, batch params) в `detm_app.ui.napari.interactive`; обновлены regression tests и human/spec roadmap под завершённый napari cutover.

### E-MNT-02 — Вынести `UiRunSettings` в config-model слой

- `id`: `E-MNT-02`
- `status`: `done`
- `priority`: `P1`
- `owner_role`: `runtime`
- `target_date`: `2026-02-18`
- `depends_on`: `[E-MNT-01]`
- `scope_in`: убрать coupling `detm_app.config -> detm_app.runner` через перенос контракта `UiRunSettings` в нейтральный config/model модуль (`detm_app/config/ui_models.py` или эквивалент).
- `scope_out`: изменение runtime semantics и UI feature set.
- `deliverables`: отдельный dataclass/contract модуль для UI settings + обновлённые импорты `config/runner/ui`.
- `api_contract_changes`: module-path change для `UiRunSettings` и связанных helper-функций.
- `tests_required`: import-boundary tests (`config` не импортирует `runner`), smoke tests загрузки preset/override для UI.
- `readout_artifacts`: `detm_app/config/app_settings.py`, новый config-model модуль, `tests/test_ui_layer_boundaries.py`.
- `risks`: неполная миграция импортов и скрытые циклы.
- `dod`: `detm_app.config.*` не содержит импортов `detm_app.runner.*`, контракт `UiRunSettings` доступен из config-model слоя.
- `readout` (2026-02-13): `UiRunSettings` вынесен в `detm_app/config/ui_models.py`; `detm_app/config/app_settings.py` переведён на `detm_app.config.ui_models.UiRunSettings`; `DetmUiRunner` перенесён в `detm_app/runtime/ui_runtime/core.py`; обновлены импорты `napari/tk/__init__`; добавлены boundary checks (`tests/test_ui_layer_boundaries.py`).

### E-MNT-03 — Viewer adapter registry в `detm_app.runner.shell`

- `id`: `E-MNT-03`
- `status`: `done`
- `priority`: `P1`
- `owner_role`: `runtime`
- `target_date`: `2026-02-20`
- `depends_on`: `[E-MNT-02]`
- `scope_in`: убрать hardcoded viewer entrypoints/imports из `shell.py` и перейти на adapter-registry (`viewer_id -> launcher contract`).
- `scope_out`: добавление новых viewer-реализаций сверх `none|napari`.
- `deliverables`: registry module + адаптированный `build_shell_contract/main` + compatibility tests.
- `api_contract_changes`: shell execution contract фиксирует registry-backed `entrypoint/viewer_options`.
- `tests_required`: `tests/test_shell_orchestrate.py`, `tests/test_main_entrypoint_routing.py`, negative tests на unknown viewer.
- `readout_artifacts`: `detm_app/runner/shell.py`, viewer registry module, updated shell tests.
- `risks`: поломка CLI routing при несовместимых viewer options.
- `dod`: `shell.py` не импортирует `detm_app.ui.*` напрямую (кроме registry wiring/lookup), контракт сборки роли viewer стабилен.
- `readout` (2026-02-13): добавлен `detm_app/runner/viewer_registry.py`; `detm_app/runner/shell.py` переведён на registry lookup (`resolve_viewer_adapter`) и launcher adapter (`run_napari_viewer`) без прямого импорта `detm_app.ui.napari.*`; добавлены проверки слоя (`test_runner_shell_uses_viewer_registry_not_direct_ui_imports`) и regression suite зелёная.

### E-MNT-04 — Unified batch orchestration service для UI

- `id`: `E-MNT-04`
- `status`: `done`
- `priority`: `P1`
- `owner_role`: `runtime`
- `target_date`: `2026-02-24`
- `depends_on`: `[E-MNT-02]`
- `scope_in`: вынести дублируемую batch-логику из `detm_app/ui/napari/interactive/__init__.py` и `detm_app/ui/tk/runner/launcher.py` в общий app-layer service.
- `scope_out`: изменение формата batch readout артефактов.
- `deliverables`: `detm_app/runner/batch_service.py` (или эквивалент), единый API запуска/отмены/логирования batch-run.
- `api_contract_changes`: общий batch service contract для UI frontends.
- `tests_required`: перенос/расширение batch tests для napari/tk с общим backend service.
- `readout_artifacts`: `detm_app/ui/napari/interactive/__init__.py`, `detm_app/ui/tk/runner/launcher.py`, новый batch service module, UI tests.
- `risks`: race conditions в cancel/poll path после унификации.
- `dod`: дублируемые batch helper-функции в UI удалены, поведение UI batch-path parity подтверждено тестами.
- `readout` (2026-02-13): добавлен общий сервис `detm_app/runner/batch_service.py` (`BatchRunRequest`, `BatchRunHandle`, `start_batch_run`, `parse_batch_symbols_csv`); napari/tk UI переведены на общий batch backend и polling contract; сохранён совместимый `_parse_symbol_csv` для napari tests; добавлены unit tests `tests/test_batch_service.py` и boundary checks `tests/test_ui_layer_boundaries.py`.

### E-MNT-05 — Декомпозиция крупных app-layer модулей

- `id`: `E-MNT-05`
- `status`: `done`
- `priority`: `P2`
- `owner_role`: `runtime`
- `target_date`: `2026-02-28`
- `depends_on`: `[E-MNT-03, E-MNT-04]`
- `scope_in`: структурная декомпозиция `detm_app/runner/headless/*`, `detm_app/ui/napari/interactive/*`, `detm_app/ui/tk/runner/*` на feature-модули.
- `scope_out`: функциональное расширение CLI/UI.
- `deliverables`: module split plan + executed split + compat imports.
- `api_contract_changes`: internal module-path changes без изменения user-facing CLI flags.
- `tests_required`: full app-layer regression (`entrypoints/shell/napari interactive/batch`).
- `readout_artifacts`: module tree diff + updated tests + import-boundary checks.
- `risks`: регрессии из-за некорректной миграции side-effects.
- `dod`: крупные модули разбиты на cohesive units; test matrix остаётся зелёной.
- `readout` (2026-02-13): выделены `detm_app/runner/headless/helpers.py` (default/symbol/steps/list utils), `detm_app/runner/headless/parser.py` (CLI parser factory), `detm_app/ui/napari/interactive/helpers.py` (quiver/policy/parse helpers), `detm_app/ui/tk/runner/launcher.py` (canonical Tk launcher) + `detm_app/ui/tk/runner/__init__.py` как compatibility wrapper; обновлены boundary tests и полный pytest snapshot зелёный.
- `readout` (2026-02-13): `detm_app/runner/headless/options.py` переведён с tuple-return на типизированный `HeadlessMainOptions`; устранён дрейф fabric-полей при резолве CLI defaults (`fabric_*_validator_ids`, `*_replica_state_paths`), в `detm_app/runner/headless/main.py` убран дублированный single/batch kwargs через `_build_run_headless_kwargs`; добавлены guards `tests/test_headless_options.py`; regression snapshot: `pytest -q -> 331 passed, 1 skipped`.
- `readout` (2026-02-13): закреплён пакетный формат decomposition: `detm_app/runner/headless/*`, `detm_app/ui/napari/interactive/*`, `detm_app/ui/tk/runner/*`; публичные import paths сохранены (`detm_app.runner.headless`, `detm_app.ui.napari.interactive`, `detm_app.ui.tk.runner`), обновлены import-boundary tests и smoke-routing tests.
- `readout` (2026-02-13): subscriber wiring для headless-run вынесен в `detm_app/runner/headless/subscribers/__init__.py` (`attach_headless_subscribers` + split `core/fabric/streaming` attach paths); `detm_app/runner/headless/main.py` оставлен orchestration-only в `run_headless` при сохранении полного CLI/API контракта.
- `readout` (2026-02-13): execution loop (`per_symbol|total`) вынесен из `detm_app/runner/headless/main.py` в `detm_app/runner/headless/executor.py` (`execute_headless_steps`); добавлены unit tests `tests/test_headless_executor.py`; полный regression snapshot остаётся зелёным (`pytest -q -> 331 passed, 1 skipped`).
- `readout` (2026-02-13): введён `RunHeadlessRequest` в `detm_app/runner/headless/request.py` и `run_headless_request(...)` в `detm_app/runner/headless/main.py`; legacy `run_headless(...)` сохранён как facade с поддержкой старого API через `**fabric_kwargs` и нормализацией defaults/unknown-keys guard.
- `readout` (2026-02-13): `main.py --help` переведён на launcher-level справку (только режимы запуска); для полного списка внутренних headless параметров добавлен явный путь `python main.py headless --help`; покрыто routing/help тестами (`tests/test_main_entrypoint_routing.py`).
- `readout` (2026-02-14): выполнен дополнительный split napari interactive слоя: монолит `detm_app/ui/napari/interactive/__init__.py` превращён в thin bootstrap/entrypoint, контроллер dock-UI вынесен в `detm_app/ui/napari/interactive/controller.py` с сохранением публичного API (`run_napari_interactive`, `_build_interactive_settings`, `_parse_symbol_csv`) и batch-контракта через `detm_app.runner.batch_service`; обновлены boundary checks `tests/test_ui_layer_boundaries.py`; regression snapshot: `pytest -q -> 331 passed, 1 skipped`.
- `readout` (2026-02-14): продолжена декомпозиция napari interactive контроллера: batch lifecycle (`start/cancel/drain/finish`) и сборка `BatchRunRequest` вынесены в `detm_app/ui/napari/interactive/flow/batch/__init__.py` (`BatchRunState`, `BatchUiInput`, `build_batch_request`), а `detm_app/ui/napari/interactive/controller.py` оставлен orchestration-слоем; обновлены boundary checks `tests/test_ui_layer_boundaries.py`; regression snapshot: `pytest -q -> 331 passed, 1 skipped`.
- `readout` (2026-02-14): выделен render flow для napari interactive: логика `state -> layers -> field/quiver/status` перенесена из `detm_app/ui/napari/interactive/controller.py` в `detm_app/ui/napari/interactive/flow/render.py` (`NapariRenderFlow`), контроллер переведён на вызов `render_flow.render(...)`; сохранён публичный entrypoint/API и поведение UI; обновлены boundary checks `tests/test_ui_layer_boundaries.py`; regression snapshot: `pytest -q -> 331 passed, 1 skipped`.
- `readout` (2026-02-14): выделен controls-builder для napari interactive: крупный блок `_build_controls` вынесен из `detm_app/ui/napari/interactive/controller.py` в `detm_app/ui/napari/interactive/flow/controls.py` (`build_interactive_controls`), контроллер оставлен orchestration-слоем и вызывает builder как thin-wrapper; сохранены публичные entrypoints/API и UI-поведение; обновлены boundary checks `tests/test_ui_layer_boundaries.py`; regression snapshot: `pytest -q -> 331 passed, 1 skipped`.
- `readout` (2026-02-14): выделен settings flow для napari interactive: логика сборки runtime config и применения UI-настроек (`_build_config_from_controls`, `_apply_settings`) вынесена из `detm_app/ui/napari/interactive/controller.py` в `detm_app/ui/napari/interactive/flow/settings.py` (`build_config_from_controls`, `apply_settings`), контроллер оставлен thin-оркестратором с делегированием; обновлены boundary checks `tests/test_ui_layer_boundaries.py`; regression snapshot: `pytest -q -> 331 passed, 1 skipped`.
- `readout` (2026-02-14): выделен actions flow для napari interactive: обработчики режимов и интерактивных действий (`_mode_is_batch`, `_on_mode_change`, `_on_apply`, `_on_reset`, `_on_step`, `_on_run_toggle`) вынесены из `detm_app/ui/napari/interactive/controller.py` в `detm_app/ui/napari/interactive/flow/actions/__init__.py` (`mode_is_batch`, `on_mode_change`, `on_apply`, `on_reset`, `on_step`, `on_run_toggle`), контроллер оставлен thin-wrapper-слоем; обновлены boundary checks `tests/test_ui_layer_boundaries.py`; regression snapshot: `pytest -q -> 331 passed, 1 skipped`.
- `readout` (2026-02-14): выделен influence flow для napari interactive: обработчики геометрии и режимов влияния (`_sync_geometry_bounds`, `_on_influence_mode_change`, `_on_influence_policy_change`) вынесены из `detm_app/ui/napari/interactive/controller.py` в `detm_app/ui/napari/interactive/flow/influence.py` (`sync_geometry_bounds`, `on_influence_mode_change`, `on_influence_policy_change`), контроллер оставлен thin-wrapper-слоем; обновлены boundary checks `tests/test_ui_layer_boundaries.py`; regression snapshot: `pytest -q -> 331 passed, 1 skipped`.
- `readout` (2026-02-14): продолжена декомпозиция orchestration-контуров napari interactive: обработчик `_on_batch_toggle` вынесен из `detm_app/ui/napari/interactive/controller.py` в `detm_app/ui/napari/interactive/flow/batch/__init__.py` (`on_batch_toggle`), UI wiring (`_build_buttons`, `_install_shortcuts`) вынесен в `detm_app/ui/napari/interactive/flow/ui_wiring.py` (`build_buttons`, `install_shortcuts`); контроллер сохранён как thin-wrapper слой; обновлены boundary checks `tests/test_ui_layer_boundaries.py`; regression snapshot: `pytest -q -> 331 passed, 1 skipped`.
- `readout` (2026-02-14): выделен widget I/O flow для napari interactive: низкоуровневые UI-хелперы (`_line`, `_read_text`, `_read_int`, `_read_float`) вынесены из `detm_app/ui/napari/interactive/controller.py` в `detm_app/ui/napari/interactive/flow/widget_io.py` (`line`, `read_text`, `read_int`, `read_float`), контроллер сохранён как thin-wrapper слой; обновлены boundary checks `tests/test_ui_layer_boundaries.py`; regression snapshot: `pytest -q -> 331 passed, 1 skipped`.
- `readout` (2026-02-14): flow-модули napari interactive консолидированы в отдельный подмодуль `detm_app/ui/napari/interactive/flow/*` (`actions.py`, `batch/*`, `controls.py`, `influence.py`, `render.py`, `settings.py`, `ui_wiring.py`, `widget_io.py`, `__init__.py`), `controller.py` переведён на импорты из `interactive.flow.*`; обновлены boundary checks `tests/test_ui_layer_boundaries.py`; regression snapshot: `pytest -q -> 331 passed, 1 skipped`.
- `readout` (2026-02-14): batch flow декомпозирован в отдельный сабпакет `detm_app/ui/napari/interactive/flow/batch/*` (`input.py`, `request.py`, `state.py`, `toggle.py`, `__init__.py`) с сохранением публичного импорта `detm_app.ui.napari.interactive.flow.batch`; обновлены boundary checks `tests/test_ui_layer_boundaries.py`; regression snapshot: `pytest -q -> 331 passed, 1 skipped`.
- `readout` (2026-02-14): controls flow дополнительно декомпозирован по страницам в `detm_app/ui/napari/interactive/flow/controls_parts/*` (`view_runtime.py`, `influence.py`, `recording_batch.py`, `__init__.py`), при этом `detm_app/ui/napari/interactive/flow/controls.py` оставлен thin-orchestrator (`build_interactive_controls` -> `add_*_page`); обновлены boundary checks `tests/test_ui_layer_boundaries.py`; regression snapshot: `pytest -q -> 331 passed, 1 skipped`.
- `readout` (2026-02-14): actions flow декомпозирован в отдельный сабпакет `detm_app/ui/napari/interactive/flow/actions/*` (`mode.py`, `interaction.py`, `__init__.py`) с сохранением публичного импорта `detm_app.ui.napari.interactive.flow.actions`; обновлены boundary checks `tests/test_ui_layer_boundaries.py`; regression snapshot: `pytest -q -> 331 passed, 1 skipped`.
- `readout` (2026-02-14): influence controls-page декомпозирован в `detm_app/ui/napari/interactive/flow/controls_parts/influence/*` (`page.py`, `joystick.py`, `__init__.py`) с сохранением публичного импорта `detm_app.ui.napari.interactive.flow.controls_parts.influence`; обновлены boundary checks `tests/test_ui_layer_boundaries.py`; regression snapshot: `pytest -q -> 331 passed, 1 skipped`.
- `readout` (2026-02-14): view/runtime controls-page декомпозирован в `detm_app/ui/napari/interactive/flow/controls_parts/view_runtime/*` (`view.py`, `runtime.py`, `__init__.py`) с сохранением публичного импорта `detm_app.ui.napari.interactive.flow.controls_parts.view_runtime`; обновлены boundary checks `tests/test_ui_layer_boundaries.py`; regression snapshot: `pytest -q -> 331 passed, 1 skipped`.
- `readout` (2026-02-14): recording/batch controls-page декомпозирован в `detm_app/ui/napari/interactive/flow/controls_parts/recording_batch/*` (`recording.py`, `batch.py`, `__init__.py`) с сохранением публичного импорта `detm_app.ui.napari.interactive.flow.controls_parts.recording_batch`; обновлены boundary checks `tests/test_ui_layer_boundaries.py`; regression snapshot: `pytest -q -> 331 passed, 1 skipped`.
- `readout` (2026-02-14): декомпозиция headless CLI слоя: fabric-аргументы парсера вынесены в `detm_app/runner/headless/parser_fabric/__init__.py` (`add_fabric_arguments`), `detm_app/runner/headless/parser.py` оставлен тонким parser-factory; резолв fabric-полей вынесен в `detm_app/runner/headless/options_fabric/__init__.py`, dataclass модели — в `detm_app/runner/headless/options_model.py`, `detm_app/runner/headless/options.py` оставлен thin-orchestrator; добавлены boundary checks `tests/test_ui_layer_boundaries.py`; regression snapshot: `pytest -q -> 332 passed, 1 skipped`.
- `readout` (2026-02-14): вынесен Tk viz/runtime flow из `detm_app/ui/tk/runner/launcher.py` в `detm_app/ui/tk/runner/flow/viz/__init__.py` (`TkVizFlow`, `install_clipboard_shortcuts`); `launcher.py` оставлен orchestration-слоем (apply/tick/mode/batch wiring) и переведён на вызовы `viz_flow.update_embedded/update_tcp/close`; обновлены boundary checks `tests/test_ui_layer_boundaries.py`; regression snapshot: `pytest -q -> 332 passed, 1 skipped`.
- `readout` (2026-02-14): вынесен Tk batch flow из `detm_app/ui/tk/runner/launcher.py` в `detm_app/ui/tk/runner/flow/batch.py` (`TkBatchFlow`: batch form, request build/start/cancel/poll/close); `launcher.py` оставлен orchestration-слоем (`mode switch` + `batch_flow.frame` + `batch_flow.close`); обновлены boundary checks `tests/test_ui_layer_boundaries.py`; regression snapshot: `pytest -q -> 332 passed, 1 skipped`.
- `readout` (2026-02-14): вынесен Tk runtime-actions flow из `detm_app/ui/tk/runner/launcher.py` в `detm_app/ui/tk/runner/flow/actions.py` (`TkRuntimeActionFlow`: `update_status`, `on_reset`, `on_step`, `on_run_toggle`, `on_mode_change`, `on_close`); `launcher.py` переведён на thin-wiring (`action_flow` callbacks + `root.protocol/trace_add`); обновлены boundary checks `tests/test_ui_layer_boundaries.py`; regression snapshot: `pytest -q -> 332 passed, 1 skipped`.
- `readout` (2026-02-14): вынесен Tk settings/config flow из `detm_app/ui/tk/runner/launcher.py` в `detm_app/ui/tk/runner/flow/settings/__init__.py` (`TkSettingsFlow`: `build_config`, `apply`, `read_invariant_streams`); `launcher.py` переведён на thin-wiring (`settings_flow.build_config/apply/read_invariant_streams`); обновлены boundary checks `tests/test_ui_layer_boundaries.py`; regression snapshot: `pytest -q -> 332 passed, 1 skipped`.
- `readout` (2026-02-14): дополнительно вынесен Tk window/layout flow: fullscreen/root-grid wiring вынесен в `detm_app/ui/tk/runner/flow/window.py` (`install_fullscreen_bindings`, `configure_root_grid`), построение `controls/viz/log` layout вынесено в `detm_app/ui/tk/runner/flow/layout.py` (`TkLauncherLayout`, `build_launcher_layout`); `launcher.py` оставлен orchestration-слоем; обновлены boundary checks `tests/test_ui_layer_boundaries.py`; regression snapshot: `pytest -q -> 332 passed, 1 skipped`.
- `readout` (2026-02-14): вынесен Tk controls/form builder из `detm_app/ui/tk/runner/launcher.py` в `detm_app/ui/tk/runner/flow/controls/__init__.py` (`TkControlVars`, `build_launcher_controls`); `launcher.py` переведён на thin-wiring и получает `tk.*Var` через `controls` контейнер для `settings/action/batch` flow; обновлены boundary checks `tests/test_ui_layer_boundaries.py`; regression snapshot: `pytest -q -> 332 passed, 1 skipped`.
- `readout` (2026-02-14): `Tk controls/form` дополнительно декомпозирован в сабпакет `detm_app/ui/tk/runner/flow/controls/*` (`model.py`, `builder.py`, `runtime.py`, `influence.py`, `recording_viz.py`, `__init__.py`) с сохранением публичного импорта `detm_app.ui.tk.runner.flow.controls`; `launcher.py` сохранён thin-orchestrator; обновлены boundary checks `tests/test_ui_layer_boundaries.py`; regression snapshot: `pytest -q -> 332 passed, 1 skipped`.
- `readout` (2026-02-14): `Tk settings/config flow` дополнительно декомпозирован в сабпакет `detm_app/ui/tk/runner/flow/settings/*` (`flow.py`, `config.py`, `apply.py`, `__init__.py`) с сохранением публичного импорта `detm_app.ui.tk.runner.flow.settings`; `launcher.py` упрощён до `TkSettingsFlow(settings, runner, controls)` без длинного kwargs-wiring списка; обновлены boundary checks `tests/test_ui_layer_boundaries.py`; regression snapshot: `pytest -q -> 332 passed, 1 skipped`.
- `readout` (2026-02-14): `Tk viz/runtime flow` дополнительно декомпозирован в сабпакет `detm_app/ui/tk/runner/flow/viz/*` (`flow.py`, `clipboard.py`, `__init__.py`) с сохранением публичного импорта `detm_app.ui.tk.runner.flow.viz`; обновлены boundary checks `tests/test_ui_layer_boundaries.py`; regression snapshot: `pytest -q -> 332 passed, 1 skipped`.
- `readout` (2026-02-14): `headless fabric parser/options` дополнительно декомпозированы из модулей `detm_app/runner/headless/parser_fabric/__init__.py` и `detm_app/runner/headless/options_fabric/__init__.py` в сабпакеты `detm_app/runner/headless/parser_fabric/*` (`flow.py`, `handshake.py`, `transport.py`, `coordination.py`, `delivery.py`, `__init__.py`) и `detm_app/runner/headless/options_fabric/*` (`flow.py`, `handshake.py`, `transport.py`, `coordination.py`, `delivery.py`, `__init__.py`) с сохранением публичных импортов `detm_app.runner.headless.parser_fabric`/`detm_app.runner.headless.options_fabric`; обновлены boundary checks `tests/test_ui_layer_boundaries.py`; regression snapshot: `pytest -q -> 332 passed, 1 skipped`.
- `readout` (2026-02-14): `headless subscriber wiring` дополнительно декомпозирован из `detm_app/runner/headless/subscribers/__init__.py` в сабпакет `detm_app/runner/headless/subscribers/*` (`flow.py`, `core.py`, `fabric.py`, `streaming.py`, `policy.py`, `__init__.py`) с сохранением публичного импорта `detm_app.runner.headless.subscribers`; обновлены boundary checks `tests/test_ui_layer_boundaries.py`; regression snapshot: `pytest -q -> 333 passed`.
- `readout` (2026-02-14): `E-MNT-05` переведён в `done`: крупные app-layer модули `detm_app/runner/headless/*`, `detm_app/ui/napari/interactive/*`, `detm_app/ui/tk/runner/*` декомпозированы в feature-пакеты с сохранением публичных import-paths; текущий regression snapshot: `pytest -q -> 333 passed`.
- `readout` (2026-02-14): post-refactor архитектурный regression sweep выполнен повторно (`pytest -q`, `tests/test_ui_layer_boundaries.py`, `tests/test_entrypoints_use_detm_app.py`, `tests/test_main_entrypoint_routing.py`); текущий snapshot: `pytest -q -> 340 passed`.
- `readout` (2026-02-14): выполнен дополнительный alignment-pass по runtime/app structural hotspots без смены API: `detm/runtime/fabric/quorum_runtime.py` разделён на `quorum_runtime_factory.py` + `quorum_runtime_coordination.py`, `detm/runtime/fabric/tcp_transport/transport.py` разгружен auth/TLS helper-модулями (`tcp_transport/auth.py`, `tcp_transport/tls.py`), lifecycle wiring `FabricHandshakeRecorder` вынесен в `detm_app/runtime/subscribers/fabric/lifecycle.py`; regression snapshots: `pytest -q tests/test_fabric_quorum_runtime.py tests/test_fabric_runtime_composer.py tests/test_fabric_tcp_transport.py tests/test_fabric_handshake_recorder.py tests/test_ui_layer_boundaries.py -> 62 passed`, `pytest -q -> 340 passed`.
- `readout` (2026-02-14): выполнен следующий alignment-pass по app runtime orchestration: flow `DetmSession.step` вынесен в `detm_app/runtime/session/step_flow.py` (класс `DetmSession` оставлен thin-wrapper), recording/invariant wiring вынесен из `detm_app/runtime/ui_runtime/core.py` в `detm_app/runtime/ui_runtime/recording.py` (публичные методы `_configure_recording`/`_configure_invariant_recording` сохранены); targeted regression snapshots: `pytest -q tests/test_level_policy_runtime.py tests/test_refinement_mvp.py tests/test_pattern_memory.py tests/test_system_watch_trace.py tests/test_commit_trace_linkage.py tests/test_ui_layer_boundaries.py -> 54 passed`, `pytest -q -> 340 passed`.
- `readout` (2026-02-14): удалены неиспользуемые пустые placeholder-пакеты/файлы pre-tag cleanup (`fallback/*`, `learning/*`, `levels/*`, `detm_logging/*`, пустые `tools/*`, пустые `tests/test_*`, пустые `visualization/*` модули); packaging config очищен от `detm_logging*` include в `pyproject.toml`; regression snapshot: `pytest -q -> 340 passed`.
- `readout` (2026-02-14): финальный pre-tag cleanup migration-артефактов: удалён legacy entrypoint `detm.py` (канонический вход только `main.py`), `tests/test_ui_layer_boundaries.py` переведён на устойчивые AST-boundary проверки вместо path-snapshot формата, удалены дублирующие import-guard тесты `tests/test_no_module_level_detm_app_imports_in_detm.py` и `tests/test_no_detm_app_imports_in_core.py`; актуальный regression snapshot: `pytest -q -> 348 passed`.

### G-FAB-01 — Delivery guarantees baseline (`at-least-once + idempotency`)

- `id`: `G-FAB-01`
- `status`: `done`
- `priority`: `P0`
- `owner_role`: `fabric`
- `target_date`: `2026-02-20`
- `depends_on`: `[]`
- `scope_in`: формализовать и закрыть end-to-end semantics `at-least-once + idempotent ingest` для commit/delivery path.
- `scope_out`: exactly-once semantics.
- `deliverables`: policy/profile для delivery guarantees; runtime wiring без двусмысленности.
- `api_contract_changes`: явная фиксация guarantee mode в runtime config/report contract.
- `tests_required`: crash/retry/replay scenarios + duplicate ingress tests.
- `readout_artifacts`: `fabric_quorum_report.json` (`delivery/idempotency` секции), `fabric_delivery_acks.jsonl`.
- `risks`: ложное чувство exactly-once из-за неполной формализации.
- `dod`: гарантия и границы описаны и подтверждены тестами/отчётами.
- `readout` (2026-02-13): добавлен явный `delivery_guarantee_mode` в runtime config path + `delivery_guarantees` секция в `fabric_quorum_report`; добавлены e2e тесты retry/replay/duplicate-ingress (`tests/test_fabric_commit_delivery.py`).

### G-FAB-02 — Durable queue/coordination baseline

- `id`: `G-FAB-02`
- `status`: `done`
- `priority`: `P0`
- `owner_role`: `fabric`
- `target_date`: `2026-02-23`
- `depends_on`: `[G-FAB-01]`
- `scope_in`: transactional durability для outbox/tracking/receipt state в single-host multi-process профиле.
- `scope_out`: multi-host distributed durable queue.
- `deliverables`: baseline durable coordination implementation + recovery сценарии.
- `api_contract_changes`: при необходимости расширение runtime config для durable backend профиля.
- `tests_required`: restart recovery, pending flush, dead-letter correctness.
- `readout_artifacts`: `fabric_dead_letters.json`, delivery tracking snapshots, recovery logs.
- `risks`: race conditions при multi-process доступе.
- `dod`: после рестарта pending deliveries корректно восстанавливаются и завершаются.
- `readout` (2026-02-13): добавлено file-backed состояние `delivery_tracking+receipt` (`fabric_delivery_tracking_state.json`) с восстановлением в runtime-composer; подтверждён restart-recovery сценарий на `FabricHandshakeRecorder` (`tests/test_fabric_handshake_recorder.py::test_fabric_handshake_recorder_recovers_pending_delivery_after_restart`).

### G-FAB-03 — Validator coordination + replay policy tiers

- `id`: `G-FAB-03`
- `status`: `done`
- `priority`: `P0`
- `owner_role`: `fabric`
- `target_date`: `2026-02-26`
- `depends_on`: `[G-FAB-01, G-FAB-02]`
- `scope_in`: tiers для replay policy (`off|sampled|strict-window`) и replicated validator coordination state.
- `scope_out`: Byzantine-grade validator federation.
- `deliverables`: policy tiers + persisted validator coordination state + coordination snapshot/reporting.
- `api_contract_changes`: replay policy fields в runtime config/report.
- `tests_required`: replay mismatch detection, tier transitions, validator coordination regressions.
- `readout_artifacts`: `commit_validation.json`, `fabric_quorum_report.json` (`replay_sampling`, `validator_coordination_state`), `validator_coordination_state.json`.
- `risks`: недетерминированный replay sampling при неправильной нормализации.
- `dod`: tiers reproducible; replay failures наблюдаемы и трассируемы.
- `readout` (2026-02-13): добавлены replay tiers `off|sampled|strict_window` в config/runtime/report; добавлена строгая window-проверка в `LocalFabricValidator`; в `fabric_quorum_report` добавлен `validator_coordination` с registry/hardening snapshot.
- `readout` (2026-02-13): добавлено persisted validator coordination state в `FabricQuorumRuntimeService` (single-file + replicated read/write quorum, restore на старте, mismatch guard по validator-set); протянуто через `FabricHandshakeRecorder.attach`, runtime composer, headless CLI/presets; добавлены regression tests на restore/quorum/CLI wiring.

### G-FAB-04 — Epoch/watermark consensus hardening

- `id`: `G-FAB-04`
- `status`: `done`
- `priority`: `P0`
- `owner_role`: `fabric`
- `target_date`: `2026-03-01`
- `depends_on`: `[G-FAB-02, G-FAB-03]`
- `scope_in`: укрепить monotonic/consensus контур для `epoch/watermark` в production profile.
- `scope_out`: replicated log с Byzantine guarantees.
- `deliverables`: deterministic decision path + fail-closed rules + consensus retry envelope.
- `api_contract_changes`: уточнение consensus decision/report contract.
- `tests_required`: non-monotonic reject tests, timeout/retry consensus tests, recovery tests.
- `readout_artifacts`: `fabric_quorum_report.json` (`epoch` секция), audit traces.
- `risks`: split-brain при ошибочной политике quorum.
- `dod`: нарушения monotonicity детектируются и не проходят commit boundary.
- `readout` (2026-02-13): добавлены `epoch consensus` retry rounds (`max_attempts`) с явной статистикой `proposals/timeouts/retries`; добавлена fail-closed валидация peer-vote payload (`commit_ref/epoch/watermark/tick`) + reject на conflicting votes; обновлены runtime config/CLI/presets и тесты (`tests/test_fabric_epoch.py`, `tests/test_fabric_epoch_consensus.py`, `tests/test_fabric_runtime_composer.py`, `tests/test_cli_steps_mode.py`).

### G-FAB-05 — Distributed validator handshake production profile

- `id`: `G-FAB-05`
- `status`: `done`
- `priority`: `P0`
- `owner_role`: `fabric`
- `target_date`: `2026-03-04`
- `depends_on`: `[G-FAB-03, G-FAB-04]`
- `scope_in`: production профиль distributed handshake поверх `CommitChainManager` и `ProofAck/TrustAck`.
- `scope_out`: full dynamic membership governance/PKI lifecycle.
- `deliverables`: profile presets + runtime enforcement и reject semantics.
- `api_contract_changes`: уточнение handshake policy contract (profile-level).
- `tests_required`: membership binding tests, reject-on-spoof tests, quorum accept/reject matrix.
- `readout_artifacts`: `fabric_acks.jsonl`, `fabric_ack_envelopes.jsonl`, `fabric_quorum_report.json`.
- `risks`: ложнопозитивные reject из-за слишком жёстких биндингов.
- `dod`: handshake профиль воспроизводим и покрыт matrix tests.
- `readout` (2026-02-13): введён profile-level контракт `handshake_profile` (`mvp|production`) с fail-closed rules для `production` (обязательный validator-set, mandatory hardening flags, binding coverage checks по auth/transport identity); профиль протянут через normalize/subscriber/composer/headless CLI/presets и отражается в `fabric_quorum_report.json` (`handshake_profile` секция); добавлены matrix/negative tests (`tests/test_fabric_handshake_recorder_config.py`, `tests/test_fabric_runtime_composer.py`, `tests/test_fabric_quorum_report.py`, `tests/test_cli_steps_mode.py`).

### F-01 — Контур накопления reaction/correction операторов

- `id`: `F-01`
- `status`: `done`
- `priority`: `P1`
- `owner_role`: `runtime`
- `target_date`: `2026-03-08`
- `depends_on`: `[G-FAB-01, G-FAB-02, G-FAB-03]`
- `scope_in`: runtime pipeline накопления correction/reaction как операторов с контролируемой reuse-политикой.
- `scope_out`: ML-heavy training pipelines.
- `deliverables`: operator accumulation contour + persistence/selection rules.
- `api_contract_changes`: новые operator metadata fields в readout/trace (если нужны).
- `tests_required`: operator accumulation, replay-safe reuse, regression на refinement.
- `readout_artifacts`: trace/readout with operator decisions.
- `risks`: накопление шумовых операторов.
- `dod`: операторы копятся и переиспользуются в reproducible runtime path.
- `readout` (2026-02-16): введён явный operator-decision contract в refinement event (`operator.id/source/selection/scope/hits/score/accepted`) и baseline совместимости `discrete_torsion_v1` (`commutator_proxy`, `torsion_score`, `torsion_flag`, `compatible`); `operator_capacity_signal_score` теперь вычисляется из фактических `hits/reuse` runtime-пути, а не только из внешнего override; добавлено rule-based selection (`torsion_guard_v1`, причина выбора в event) и bounded runtime persistence (`operator_decision_history`, max 256) для replay/analysis; параметры selection/persistence вынесены в `LevelPolicy` (`refinement_operator_torsion_threshold`, `refinement_operator_torsion_guard_enabled`, `refinement_operator_history_limit`) и протянуты в runtime; добавлен отдельный artifact-first поток `operator_decisions.jsonl` (`trace_ref`, `decision_count/summary`, policy-aware retention через `artifact_storage_policy.operator_decisions`); в `watch_contract` добавлены агрегаты `operator_decision_count/operator_reuse_count/operator_search_count/operator_reuse_rate/operator_torsion_guard_block_count/operator_torsion_flag_count/operator_torsion_score_mean`; покрыто тестами `tests/test_operator_decision_writer.py`, `tests/test_artifact_storage_policy.py`, `tests/test_level_policy_runtime.py`, `tests/test_pattern_memory.py`, `tests/test_refinement_mvp.py`, `tests/test_refinement_operator_contract.py`, `tests/test_watch_contract_writer.py`.

### F-02 — Переносимость операторов

- `id`: `F-02`
- `status`: `done`
- `priority`: `P1`
- `owner_role`: `runtime`
- `target_date`: `2026-03-10`
- `depends_on`: `[F-01]`
- `scope_in`: критерии и тест-контур переносимости (`hold_rate`, `operator_reuse`, `transferability`).
- `scope_out`: глобальный auto-tuning всей политики runtime.
- `deliverables`: portability criteria + acceptance thresholds.
- `api_contract_changes`: readout metrics contract для portability.
- `tests_required`: cross-regime transfer scenarios и baseline comparison.
- `readout_artifacts`: metrics reports по `hold_rate/operator_reuse/transferability`.
- `risks`: Goodhart на одном показателе.
- `dod`: переносимость измерима и не сводится к единичному KPI.
- `readout` (2026-02-16): в `operator_decisions.jsonl` добавлена portability-панель (`hold_rate`, `operator_reuse`, `transferability` + counts) с накоплением по runtime-потоку; для панели введён формальный acceptance-gate (`thresholds` + `acceptance.passed/failed_signals`), где baseline cross-regime сценарий (`portable` vs `strict`) покрыт в `tests/test_operator_portability_panel.py`; поток подключён в headless/UI subscribers и подчиняется `artifact_storage_policy.operator_decisions`.

### F-03 — Anti-Goodhart readout и `goodhart_flag`

- `id`: `F-03`
- `status`: `done`
- `priority`: `P1`
- `owner_role`: `runtime`
- `target_date`: `2026-03-12`
- `depends_on`: `[F-01, F-02]`
- `scope_in`: runtime anti-Goodhart панель, rule-based `goodhart_flag`, policy reaction.
- `scope_out`: внешние продуктовые KPI.
- `deliverables`: multi-signal readout protocol в runtime.
- `api_contract_changes`: `goodhart_flag`/panel fields в readout artifact contract.
- `tests_required`: degradation detection tests, false-positive/false-negative checks.
- `readout_artifacts`: readout panel snapshots + trace policy events.
- `risks`: шумные сигналы и переалертинг.
- `dod`: flag срабатывает по формализованным правилам и покрыт тестами.
- `readout` (2026-02-16): в portability-панель `operator_decisions.jsonl` добавлен multi-signal anti-Goodhart блок (`anti_goodhart`) с формализованным правилом `goodhart_flag=(d_target>0) and (degraded_signals>=2)` для `target=operator_reuse`; учитываются деградации `hold_rate/transferability/torsion_health`, публикуются `target_delta`, `degraded_signals`, `policy_reaction` (`downweight_target_signal`, `enable_extended_outerfields_audit`, profile-hint) и applicability (`cold_start|runtime_panel|disabled`); anti-Goodhart поведение стало policy-driven через `LevelPolicy` knobs (`anti_goodhart_enabled`, `anti_goodhart_target_signal`, `anti_goodhart_min_target_delta`, `anti_goodhart_min_degraded_signals`, `anti_goodhart_degradation_epsilon`, `anti_goodhart_policy_reaction_enabled`, `anti_goodhart_prefer_runtime_profile`) и теперь реакция реально влияет на runtime-adaptive контур (`session._runtime_adaptive_profile/window`) при `policy_reaction.apply=true`; anti-Goodhart snapshot также экспортируется в `watch_trace/watch_contract` (`policy.anti_goodhart` + `watchpoints.anti_goodhart*`) и формализован typed readout-контрактом `AntiGoodhartSnapshot/AntiGoodhartReaction` в `detm/runtime/watch_contract.py`; exploration-horizon contour (`exploration_horizon_ticks`, `horizon_start_tick`, `horizon_break_reason`, `horizon_recovery_cost_ticks`) теперь тоже живёт в runtime/watch/readout и покрыт рядом тестов вместе с anti-Goodhart path. Добавлены тесты детекции/ложных срабатываний `tests/test_operator_anti_goodhart.py`, policy wiring `tests/test_operator_decision_writer.py`, runtime reaction scenario `tests/test_level_policy_runtime.py`, watch trace/contract checks `tests/test_system_watch_trace.py`, `tests/test_watch_contract_writer.py`, typed contract checks `tests/test_watch_contract_anti_goodhart.py` и интеграционный smoke `tests/test_operator_portability_panel.py`.

### G-ND-01 — Эволюция `DETMState` к `shape[N]`

- `id`: `G-ND-01`
- `status`: `done`
- `priority`: `P2`
- `owner_role`: `runtime`
- `target_date`: `2026-03-14`
- `depends_on`: `[G-FAB-05]`
- `scope_in`: backward-compatible миграция state/config с `width/height` на `shape`.
- `scope_out`: удаление 2D compatibility на этом шаге.
- `deliverables`: state/config migration spec + implementation.
- `api_contract_changes`: `DETMConfig`/serialization schema extension.
- `tests_required`: backward compatibility tests + 3D smoke tests.
- `readout_artifacts`: schema version report + migration test logs.
- `risks`: поломка существующих 2D сценариев.
- `dod`: 2D и N-D контуры работают параллельно без регрессий.
- `readout` (2026-03-20): backward-compatible migration slice для `state/config` закрыт как отдельный этап. В `DETMConfig` введён канонический `shape[N]` при сохранении `width/height` как alias последних двух осей, а `DETMFieldState` и `serialization/state.py` сохраняют и восстанавливают N-D shape без потери 2D lattice-совместимости. Публичный API создаёт N-D state через `reset(...)`, а `digest(...)`/`digest_blob(...)` проецируют N-D поля в каноническую 2D plane readout по trailing axes; дальнейшее обобщение runtime/refinement/outerfields было вынесено и закрывалось уже в `G-ND-02`. Добавлены RED/GREEN тесты `tests/test_nd_state_shape.py` и расширен API regression в `tests/test_integration_contract.py`; соседние regression-срезы `tests/test_state_schema_migration.py`, `tests/test_refinement_mvp.py`, `tests/test_level_policy_runtime.py -k "roundtrip or anti_goodhart or runtime_adaptive"` остаются зелёными.

### G-ND-02 — N-D контракты serialization/refinement/outerfields

- `id`: `G-ND-02`
- `status`: `done`
- `priority`: `P2`
- `owner_role`: `runtime`
- `target_date`: `2026-03-16`
- `depends_on`: `[G-ND-01]`
- `scope_in`: обобщение runtime контрактов и артефактов на N-D.
- `scope_out`: оптимизация производительности N-D.
- `deliverables`: updated contracts + adapters.
- `api_contract_changes`: N-D serialization/refinement/outerfields contracts.
- `tests_required`: parity tests (numpy/torch) + ND artifact validation.
- `readout_artifacts`: ND trace/outerfields artifacts.
- `risks`: неконсистентность артефактов между backend-ами.
- `dod`: N-D контракты валидны и совместимы с существующими проверками.
- `readout` (2026-03-20): bounded N-D runtime/contracts slice закрыт в пределах текущего канона. В `diagnostics/attractors.py`, `api/step_flow.py`, `refinement/pipeline/detect.py` и `metrics/boundary_flux.py` убраны жёсткие `reshape(H,W)` предпосылки: эти слои используют каноническую 2D-проекцию N-D полей по trailing axes, усредняя leading axes. Дополнительно `NumpyBackend` и `TorchBackend` умеют эволюционировать N-D state plane-wise по trailing `(H,W)` axes, influence-path обобщён на N-D через broadcast по leading axes для mask-based символов и plane-wise применение для `joystick_field`/`source_sink`, а refinement-path выполняет correction plane-wise по каждому trailing `(H,W)` slice и эмитит отдельные refinement-events с `plane_index`. Это завершает именно bounded transition-контракт для N-D runtime/serialization/refinement/outerfields и не объявляет richer cross-plane semantics каноном. Добавлены tests `tests/test_nd_projection_runtime.py`, ND detect/correction coverage в `tests/test_refinement_pipeline_steps.py` и `tests/test_refinement_mvp.py`, ND integration coverage в `tests/test_integration_contract.py`, backend parity check в `tests/test_numpy_torch_parity.py` и ND influence tests в `tests/test_influence.py`; regression-срезы `tests/test_level_policy_runtime.py`, `tests/test_system_watch_trace.py`, `tests/test_watch_contract_writer.py`, `tests/test_ui_learning_runtime.py` остаются зелёными.

### G-ND-03 — UI projection adapters для N-D

- `id`: `G-ND-03`
- `status`: `done`
- `priority`: `P2`
- `owner_role`: `runtime`
- `target_date`: `2026-03-18`
- `depends_on`: `[G-ND-02]`
- `scope_in`: проекции N-D -> 2D для текущих napari/readout consumers.
- `scope_out`: новые UI режимы и редакторы.
- `deliverables`: projection adapters + compatibility notes.
- `api_contract_changes`: projection metadata в watch/viz payload.
- `tests_required`: napari projection compatibility tests.
- `readout_artifacts`: viewer snapshots + projection logs.
- `risks`: потеря значимых сигналов при проекции.
- `dod`: текущие adapter-consumers не ломаются на N-D данных и явно показывают projection semantics вместо маскировки projected 2D view под native lattice.
- `readout` (2026-03-20): bounded adapter-layer для `G-ND-03` закрыт. `watch_trace` и `watch_contract` публикуют `projection` metadata (`source_shape`, `projected_shape`, `collapsed_axes`, `collapsed_plane_count`, `reduction`), `WatchContractWriter` строит `outerfields` для N-D state по канонической 2D-проекции по trailing axes с той же metadata в `outerfields.meta`, а UI/readout слой (`learning_snapshot`, compact/multiline learning status) показывает projected plane как projection, а не как native 2D lattice. В napari `state_to_layers(...)` по умолчанию корректно проецирует N-D state в 2D и принимает explicit `plane_index` для UI-only просмотра, interactive controls получили bounded plane selector (`mean` или конкретный leading-axis plane), а `NapariGraphDock` продолжает читать canonical telemetry из `learning_snapshot`, отдельно вычисляет optional `visual_energy_*` series только из текущей rendered plane и маркирует status как `telemetry=<canonical projection>` + `view=<selected plane>`. Embedded Tk viz panel больше не 2D-only: он читает ту же каноническую projection для N-D state и показывает `proj=` suffix в status, не вводя новых plane-selection semantics. Это завершает именно compatibility/adapter слой и намеренно не притворяется full N-D UI: selector влияет только на visual field projection, без richer cross-plane semantics, без multi-plane sync и без смены канонического `mean_leading_axes` watch/readout contract. Добавлены regression tests `tests/test_system_watch_trace.py`, `tests/test_watch_contract_writer.py`, `tests/test_ui_learning_runtime.py`, `tests/test_napari_subscriber_path.py`, `tests/test_napari_interactive_controls.py`, `tests/test_napari_graph_flow.py` и `tests/test_tk_panel_flow.py`; соседние `tests/test_integration_contract.py` остаются зелёными.

### G-RND-01 — Local-first + validation-sync спецификация

- `id`: `G-RND-01`
- `status`: `todo`
- `priority`: `P2`
- `owner_role`: `fabric`
- `target_date`: `2026-03-08`
- `depends_on`: `[G-FAB-04, G-FAB-05]`
- `scope_in`: отдельный R&D spec local-first + validation-sync на базе текущих DETM контрактов.
- `scope_out`: непосредственное включение в canonical runtime API.
- `deliverables`: protocol note с границами `prod-scope vs rnd-scope`.
- `api_contract_changes`: не обязательно (doc-first), только если явно утверждено отдельным RFC.
- `tests_required`: concept-level scenario matrix, без обязательной кодовой реализации в этой задаче.
- `readout_artifacts`: R&D спецификация и acceptance matrix.
- `risks`: смешение R&D и production в одном контуре.
- `dod`: протокол описан как отдельный экспериментальный трек без влияния на канон.

### RT-MNT-01 — Декомпозиция `detm/runtime/refinement/apply.py`

- `id`: `RT-MNT-01`
- `status`: `done`
- `priority`: `P1`
- `owner_role`: `runtime`
- `target_date`: `2026-03-05`
- `depends_on`: `[G-FAB-05]`
- `scope_in`: разрезать `maybe_apply_refinement` на pipeline-level этапы (`detect -> roi -> correction -> metrics`) с явными контрактами.
- `scope_out`: изменение математической логики refinement.
- `deliverables`: новые refinement submodules + orchestrator + backward-compatible entrypoint.
- `api_contract_changes`: internal runtime API split для refinement helper contracts.
- `tests_required`: existing refinement regression + unit tests на каждый pipeline step.
- `readout_artifacts`: `detm/runtime/refinement/apply.py`, `detm/runtime/refinement/pipeline/*.py`, `tests/test_refinement_mvp.py`.
- `risks`: незаметная смена порядка применения correction operators.
- `dod`: `maybe_apply_refinement` либо тонкий orchestration-layer, либо полностью заменён модулярным pipeline без регрессий.
- `readout` (2026-02-14): `refinement/apply.py` переведён в thin-facade и делегирует в pipeline-подмодуль `detm/runtime/refinement/pipeline/*` (`contracts.py`, `detect.py`, `roi.py`, `correction.py`, `metrics.py`, `orchestrator.py`) с явными stage-контрактами `detect -> roi -> correction -> metrics`; добавлены step-level unit tests `tests/test_refinement_pipeline_steps.py`; regression snapshots: `pytest -q tests/test_refinement_pipeline_steps.py -> 4 passed`, `pytest -q tests/test_refinement_mvp.py -> 18 passed`, `pytest -q -> 337 passed`.

### RT-MNT-02 — Разделение `detm/runtime/level_policy/*`

- `id`: `RT-MNT-02`
- `status`: `done`
- `priority`: `P1`
- `owner_role`: `runtime`
- `target_date`: `2026-03-07`
- `depends_on`: `[RT-MNT-01]`
- `scope_in`: разделить monolithic level-policy слой на model/normalization/decision модули с минимизацией cross-field coupling.
- `scope_out`: изменение внешнего формата policy payload.
- `deliverables`: `model.py` + `normalization_build.py`/`normalization_inputs.py`/`normalization_serialize.py` + `decision_runtime_adaptive.py`/`decision_guard.py`/`decision_signals.py` и обновлённые импорты runtime.
- `api_contract_changes`: internal module-path changes для `LevelPolicy` helper API.
- `tests_required`: `tests/test_level_policy_runtime.py` + compatibility tests `from_dict/to_dict/decide_runtime_adaptive`.
- `readout_artifacts`: split modules under `detm/runtime/level_policy/*`, updated tests.
- `risks`: несовместимость defaults при переносе normalization logic.
- `dod`: большие методы `from_dict/to_dict/decide_runtime_adaptive` декомпозированы, поведение подтверждено regression suite.
- `readout` (2026-02-14): контракты вынесены в `detm/runtime/level_policy/model.py`, normalization/serialization вынесены в `detm/runtime/level_policy/normalization_build.py`, `normalization_inputs.py`, `normalization_serialize.py`, runtime-adaptive decision-логика вынесена в `detm/runtime/level_policy/decision_runtime_adaptive.py` (+ `decision_guard.py`, `decision_signals.py`); публичный импорт `detm.runtime.level_policy` сохранён; regression snapshots: `pytest -q tests/test_level_policy_runtime.py -> 15 passed`, `pytest -q -> 337 passed`.

### RT-MNT-03 — Декомпозиция Fabric composer/normalize path

- `id`: `RT-MNT-03`
- `status`: `done`
- `priority`: `P1`
- `owner_role`: `fabric`
- `target_date`: `2026-03-09`
- `depends_on`: `[G-FAB-05]`
- `scope_in`: декомпозировать `detm/runtime/fabric/runtime_composer/composer.py` и `detm/runtime/fabric/handshake_recorder_config/*` в отдельные сервисы/нормализаторы.
- `scope_out`: изменение fabric handshake policy semantics.
- `deliverables`: composer wiring modules (`transport/delivery/epoch/handshake`) + normalized config helpers per concern.
- `api_contract_changes`: internal config-normalization API split.
- `tests_required`: `tests/test_fabric_runtime_composer.py`, `tests/test_fabric_handshake_recorder_config.py`, CLI wiring tests.
- `readout_artifacts`: updated fabric composer modules, preserved `fabric_quorum_report` sections.
- `risks`: частичная миграция и скрытые fallback ветки.
- `dod`: composer/normalize path разбит на изолированные блоки; покрытие ключевых веток тестами сохранено.
- `readout` (2026-02-14): `detm/runtime/fabric/runtime_composer/composer.py` переведён в thin-orchestrator, а composition path вынесен в подмодули `runtime_composer/state.py`, `delivery.py`, `artifact.py`, `transport.py`, `validator.py`, `epoch.py`, `quorum.py`, `services.py`, `reporting.py`; сохранены monkeypatch targets для regression tests (`open_fabric_transport`, `FabricQuorumRuntimeService.from_policy_settings`) и публичный API `compose_fabric_handshake_runtime`; normalization path вынесен в пакет `detm/runtime/fabric/handshake_recorder_config/*` (`flow.py`, `helpers.py`, `profile.py`); regression snapshots: `pytest -q tests/test_fabric_runtime_composer.py -> 10 passed`, `pytest -q tests/test_fabric_handshake_recorder_config.py -> 5 passed`, `pytest -q -> 337 passed`.

### RT-MNT-04 — Завершить schema migration в `serialization/*`

- `id`: `RT-MNT-04`
- `status`: `done`
- `priority`: `P1`
- `owner_role`: `runtime`
- `target_date`: `2026-03-12`
- `depends_on`: `[RT-MNT-02]`
- `scope_in`: убрать placeholder `migrate_state(...)` и ввести формализованный migration path между schema versions.
- `scope_out`: полная redesign binary format.
- `deliverables`: migration registry + versioned adapters + compatibility tests.
- `api_contract_changes`: explicit migration contract for `serialize_state/deserialize_state`.
- `tests_required`: forward/backward migration tests across supported schema versions.
- `readout_artifacts`: `detm/runtime/serialization/*`, schema tests, migration report note.
- `risks`: silent data corruption при неполной миграции.
- `dod`: migration path реализован и покрыт тестами; placeholder ветка удалена.
- `readout` (2026-02-14): placeholder `migrate_state(...)` удалён; в `detm/runtime/serialization/*` добавлен формализованный migration registry с version graph и adapters (`0.0.0` legacy unversioned <-> `1.0.0`), `deserialize_state` теперь выполняет автоматическую миграцию legacy payload к канонической схеме, а `migrate_state(blob, from_version, to_version)` валидирует embedded-version и применяет versioned adapters; добавлены compatibility tests `tests/test_state_schema_migration.py`; публичные экспорты `migrate_state` добавлены в `detm.runtime.api`/`detm.runtime`; regression snapshots: `pytest -q tests/test_state_schema_migration.py -> 3 passed`, `pytest -q tests/test_integration_contract.py -> 2 passed`, `pytest -q -> 340 passed`.

### PUB-01 — Demo assets для README и docs

- `id`: `PUB-01`
- `status`: `todo`
- `priority`: `P0`
- `owner_role`: `docs`
- `target_date`: `2026-02-28`
- `depends_on`: `[]`
- `scope_in`: добавить 3-5 наглядных GIF/MP4 демо (рост структуры, коарсинг, устойчивый объект) и встроить в `README.md`/`docs/media`.
- `scope_out`: изменение runtime-логики, новые алгоритмы.
- `deliverables`: curated demo assets + обновлённый блок preview в `README.md`.
- `api_contract_changes`: нет.
- `tests_required`: smoke-check ссылок/путей в docs, ручной sanity просмотр.
- `readout_artifacts`: `docs/media/*`, `README.md`.
- `risks`: визуализации не отражают каноничный режим (маркетинг вместо факта).
- `dod`: минимум 3 воспроизводимых демо-артефакта с подписью параметров запуска и ссылкой на сценарий.

### PUB-02 — Каноничный пакет визуальных пресетов

- `id`: `PUB-02`
- `status`: `todo`
- `priority`: `P0`
- `owner_role`: `runtime`
- `target_date`: `2026-03-03`
- `depends_on`: `[PUB-01]`
- `scope_in`: зафиксировать 2-3 публичных пресета (`classic_coarsing`, `stable_object`, `channel_tunnel`) с командами запуска и ожидаемыми артефактами.
- `scope_out`: добавление новых фундаментальных механик.
- `deliverables`: preset configs + короткие runbooks + ссылка в README/experiments docs.
- `api_contract_changes`: нет (config-level only).
- `tests_required`: reproducibility smoke (`headless` runs с фиксированными seed) + проверка наличия expected artifacts.
- `readout_artifacts`: `experiments/*`, `runs/*` exemplar paths, docs references.
- `risks`: пресеты окажутся нестабильными между окружениями/backend.
- `dod`: каждый пресет воспроизводится одной командой и даёт documented artifacts (`catalog/metrics/summary/final_state`).

### PUB-03 — One-page overview (RU/EN)

- `id`: `PUB-03`
- `status`: `todo`
- `priority`: `P1`
- `owner_role`: `docs`
- `target_date`: `2026-03-05`
- `depends_on`: `[PUB-01]`
- `scope_in`: создать одностраничный обзор проекта (`что это`, `что это не`, `как запустить`, `куда смотреть дальше`) на RU/EN.
- `scope_out`: глубокая переработка canonical docs/cards.
- `deliverables`: `docs/rus/00_overview/one_pager.md`, `docs/eng/00_overview/one_pager.md`, ссылки из `README.md`/`docs/README.md`.
- `api_contract_changes`: нет.
- `tests_required`: docs link check.
- `readout_artifacts`: one-pager files + README/docs index updates.
- `risks`: дублирование и рассинхрон с canonical документацией.
- `dod`: one-pager синхронизирован с roadmap и launch-командами, ссылки валидны.

### QLT-01 — Code-level docstrings и type hints (runtime core)

- `id`: `QLT-01`
- `status`: `todo`
- `priority`: `P1`
- `owner_role`: `runtime`
- `target_date`: `2026-03-10`
- `depends_on`: `[]`
- `scope_in`: усилить docstrings/type hints в ключевых runtime-контрактах (`detm/runtime/api/*`, critical services в `detm_app/runtime/*`).
- `scope_out`: масштабный refactor архитектуры и изменение runtime semantics.
- `deliverables`: обновлённые сигнатуры и docstrings + краткая note о coverage зон.
- `api_contract_changes`: нет (аннотации/док-комментарии, без изменения поведения).
- `tests_required`: regression suite + static type check smoke (если включён).
- `readout_artifacts`: updated runtime modules, test snapshot.
- `risks`: расхождение docstrings с фактическим поведением.
- `dod`: покрыты основные public API точки и orchestrator-контракты, regression без изменений поведения.

### DAGM-01 — RFC: general-graph runtime трек

- `id`: `DAGM-01`
- `status`: `todo`
- `priority`: `P2`
- `owner_role`: `docs`
- `target_date`: `2026-03-15`
- `depends_on`: `[G-ND-01]`
- `scope_in`: подготовить RFC/spec для отдельного runtime-трека DAGM на произвольном графе (границы с DETM-lattice, миграционный план, non-goals).
- `scope_out`: реализация production-ready graph runtime в текущем цикле.
- `deliverables`: RFC документ + decision matrix (benefits/risks/cost) + критерии старта отдельного workstream.
- `api_contract_changes`: doc-level proposal only.
- `tests_required`: concept-level scenario matrix.
- `readout_artifacts`: RFC в `docs/rus/90_notes/*` (и EN short note при необходимости).
- `risks`: преждевременный распыл фокуса до закрытия F/N-D.
- `dod`: RFC явно разделяет `research idea` vs `execution plan`, без изменения канона текущего runtime.

## PM Registry (done doc-items)

### DOC-01 — Полная переработка структуры roadmap

- `id`: `DOC-01`
- `status`: `done`
- `priority`: `P0`
- `owner_role`: `docs`
- `target_date`: `2026-02-16`
- `depends_on`: `[]`
- `scope_in`: `Scope/Status Snapshot/Workstreams/PM Registry/Risks/Readout`.
- `scope_out`: кодовые изменения runtime.
- `deliverables`: текущий `ROADMAP V2`.
- `api_contract_changes`: нет.
- `tests_required`: структурная проверка документа.
- `readout_artifacts`: `docs/rus/ROADMAP.md`.
- `risks`: потеря контекста при переносе старых разделов.
- `dod`: новый формат принят и закрывает общие пункты.
- `readout` (2026-02-13): синхронизированы архитектурные и launch-документы после migration `detm.run -> detm_app.runtime`: обновлены `README.md`, `docs/rus/architecture.md`, `docs/eng/architecture.md`, `docs/rus/00_overview/architecture.md`, `docs/rus/30_architecture/target_architecture_synthesis.md`, `docs/rus/30_architecture/commit_protocol.md`, `docs/eng/integration_contract.md`, `docs/rus/integration_contract.md`, `.codex/PROMT_SHORT.md`.
- `readout` (2026-02-14): актуализированы статусные карточки program-layer экспериментов (`docs/rus/50_experiments/{00,01,02}_*.md`, `docs/eng/40_experiments/{00,01,02}_*.md`, README-индексы), а также регенерирован единый mega UML (`docs/uml/ALL_PROJECT_UML_MEGA.puml`) под текущий layout `session/*`, `ui_runtime/*`, `subscribers/*`, `serialization/*`, `fabric/*`.

## Imported from game: implemented vs pending

### Implemented in DETM

1. `System Trace + Watch Trace + trace_ref`
- Evidence: `detm_app/runtime/subscribers/trace/*`, `detm_app/runtime/subscribers/watch/*`, `detm/runtime/watch_contract.py`, `tests/test_system_watch_trace.py`.

2. Artifact-first watch contract (`OuterFieldsRef` linkage)
- Evidence: `detm/runtime/watch_contract.py`, `tests/test_watch_contract_writer.py`, `docs/rus/30_architecture/OuterFields_and_Subscriptions.md`.

3. Pattern pruning/memory contour
- Evidence: `detm/runtime/pattern_memory/*`, `tests/test_pattern_memory.py`, `docs/rus/ROADMAP.md` history.

4. Commit/envelope/quorum decomposition style
- Evidence: `detm/runtime/commit_packet.py`, `detm/runtime/fabric/*`, `tests/test_fabric_*.py`.

### Pending / partial (R&D or debt)

1. `local-first + validation-sync` как отдельный protocol track
- Status: `pending (R&D)`
- Evidence: open items `G-RND-01`, `docs/rus/ROADMAP.md` historical notes.

2. Full packet triplet parity (`commit/correction/influence`) как единый node/fabric protocol level
- Status: `partial`
- Evidence: `CommitPacket` реализован; `Correction/Influence` как отдельные protocol packets в DETM runtime не доведены до parity уровня `game` docs.

3. Runtime anti-Goodhart code contour
- Status: `baseline implemented`
- Evidence: `detm_app/runtime/anti_goodhart.py`, `detm_app/runtime/session/adaptive.py`, `detm/runtime/watch_contract.py`, `tests/test_operator_anti_goodhart.py`, `tests/test_watch_contract_anti_goodhart.py`.

## Risks Register

- `R-01` Переоценка зрелости fabric (MVP трактуется как production).
- `R-02` Расфокусировка между P0 fabric и P1/P2 треками F/N-D.
- `R-03` Регрессии 2D runtime при миграции к N-D.
- `R-04` Goodhart-оптимизация метрик без реального улучшения динамики.
- `R-05` Смешение R&D (`local-first+validation-sync`) и canonical runtime решений.
- `R-06` Скрытые циклы зависимостей между `config/runner/ui` при app-layer refactor.
- `R-07` Functional drift при декомпозиции крупных `detm/runtime` модулей.

## Readout и контроль исполнения

## Обязательные readout артефакты

- `trace.jsonl` (System Trace)
- `watch_trace.jsonl`
- `watch_contract.jsonl`
- `commits.jsonl` / `commits_audit.jsonl`
- `commit_validation.json`
- `fabric_quorum_report.json`
- `fabric_acks.jsonl`
- `fabric_delivery_acks.jsonl`
- `fabric_dead_letters.json`

## Обязательные проверки по workstream-ам

1. Структурная проверка roadmap
- каждый open-item содержит все поля `ROADMAP Item v2`.
- нет open-item без `owner_role` и `target_date`.

2. Логическая проверка зависимостей
- у каждого `P0` item заполнен `depends_on`.
- циклы зависимостей запрещены.

3. Трассируемость
- каждый item ссылается на конкретные модули/артефакты/тесты.
- для каждого item указан минимум один readout-файл или test command.

4. Проверка import-claims из `game`
- claim `implemented` подтверждён ссылкой на DETM code/tests.
- claim `pending` явно помечен как R&D/debt.

## Календарь weekly checkpoints

- `2026-02-16` — структура roadmap и P0 gate review.
- `2026-02-23` — delivery+durability gate (`G-FAB-01/02`).
- `2026-03-02` — validator/epoch gate (`G-FAB-03/04`).
- `2026-03-09` — handshake profile + старт F (`G-FAB-05`, `F-01`).
- `2026-03-16` — F metrics/anti-Goodhart + N-D kickoff (`F-02/F-03`, `G-ND-01/02`).
- `2026-03-23` — app/runtime refactor gate (`E-MNT-02..05`, `RT-MNT-01..04`).

## Принятые допущения

- Объём: полная переработка roadmap.
- Детализация: engineering spec.
- PM-поля: включены полностью.
- Owner: role-based, без персоналий.
- Даты: абсолютные (`YYYY-MM-DD`).
- Порядок исполнения: Fabric baseline -> F -> N-D.
- Delivery target: `at-least-once + idempotency`.
- Deployment baseline: `single-host multi-process`.

## Основной контрольный вопрос

> Приближает ли конкретное изменение DETM к целевой архитектуре,
> или закрепляет переходный путь как постоянный?

