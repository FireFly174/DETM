# DETM: контракт интеграции

English version: `docs/eng/integration_contract.md`

Этот документ фиксирует минимальный API и требования воспроизводимости, необходимые для подключения DETM к внешним рантаймам (ACGS Scheduler, ComfyUI и др.). DETM остаётся чистой L0‑динамикой и не знает про UI/оркестраторы: извне она видит только конфигурацию, сиды, влияния и отдаёт наблюдаемые величины.
Важно: данный контракт **не описывает модель времени, инварианты или коарсенинг**.
Он фиксирует лишь минимальный интерфейс взаимодействия с L0-динамикой.

Канонические определения:
- инварианты как спектральные операторы:
  `docs/rus/20_mechanisms/invariants_as_spectral_operators.md`
- глобальное и внутреннее время:
  `docs/rus/20_mechanisms/coarsener_and_global_time.md`
- контракт исполнения:
  `docs/rus/30_architecture/runtime_api.md`

## Базовый API
- `reset(config: DETMConfig, seed: int) -> DETMState`
- `step(state: DETMState, influence: DETMInfluence | None, n_ticks: int, rng: np.random.Generator | None = None) -> tuple[DETMState, DETMObservables]`
- `digest(state: DETMState) -> DETMSignature`
- `serialize_state(state: DETMState) -> bytes`
- `deserialize_state(blob: bytes) -> DETMState`
- `get_schema_versions() -> dict[str, str]`

Примечание о времени:

`n_ticks` является **запросом на продвижение глобального времени**,
а не указанием на физическое или внутреннее время модели.

Интерпретация тиков, выбор уровня детализации
и применение коарсенинга остаются внутренней ответственностью рантайма.

Допускаются алиасы `serialize(state)` / `deserialize(blob)` как более короткие имена,
но их сигнатуры и поведение должны быть идентичны `serialize_state`/`deserialize_state`.

### UML‑эскиз

```mermaid
classDiagram
  class DETMConfig
  class DETMState
  class DETMInfluence
  class DETMObservables
  DETMConfig --> DETMState : reset()
  DETMState --> DETMObservables : step()
  DETMState --> DETMSignature : digest()
```

### Детерминизм и воспроизводимость
- **Единый RNG**: все стохастические операции принимают `rng` явно (или используют `state.rng_state`). Никаких скрытых `np.random`/`torch.rand`.
- **Идентичные входы → идентичные подписи**: одинаковый `seed` и одна и та же последовательность `influence` должны давать одинаковый `digest`/`signature`.(при одинаковом уровне представления).
Контракт не требует совпадения внутренних траекторий при различном уровне детализации, если итоговые подписи и инварианты совпадают.

### Конфигурация (промт 1.2)
- `DETMConfig` (dataclass/pydantic) содержит `config_version` и параметры решётки/динамики.
- `DETMConfig.backend`: выбирает численный бэкенд (`"torch"` предпочтителен, `"numpy"` как эталон/фолбэк).
- `DETMConfig.device`: `"cpu"`/`"cuda"`/`"cuda:0"` и т.п.; при отсутствии CUDA бэкенд должен автоматически деградировать до CPU (или до `numpy`).
- Любое изменение схемы → bump minor версии.
- Методы `to_dict()/from_dict()` фиксируют сериализуемый формат.

## Состояние (промты 2.1–2.3)
- Всё L0‑состояние собрано в едином `DETMState`: поля `E`, `τ` (если используется), дополнительные карты, внутреннее время, счётчики, `rng_state`.
- Численные поля (`E/S/τ`) принадлежат **бэкенду**: это могут быть `numpy.ndarray` или `torch.Tensor`. Бэкенд выполняет только переход
  «текущее состояние → будущее состояние» на `n_ticks` и **не приводит** состояние к единому формату (конверсия/сравнение/трансформации делаются снаружи).
- Сериализация: `serialize_state(state) -> bytes` (msgpack/npz) и `deserialize_state(blob) -> state` с `state_version` для forward‑compatibility. Смоук‑тест: `serialize→deserialize→digest` совпадает.
- `digest(state) -> DETMSignature`: компактный вектор (8–32 числа): энергия, энтропия/гладкость, доминирующая мода, центр массы, устойчивость/периодичность при наличии.
Важно: `DETMState` не является полной физической историей системы.

Состояние:
- представляет собой текущий срез динамики;
- не гарантирует достаточного спектрального разрешения;
- может быть временно заменено развёрткой более низкого уровня
  при необходимости refinement.

Хранение и восстановление инвариантов
не входит в обязанности интеграционного контракта.

## Influence API (промты 3.1–3.2)
Influence описывает **внешнее воздействие**,
а не команду и не директиву исполнения.

DETM не гарантирует:
- немедленную реакцию;
- линейную пропорциональность ответа;
- отсутствие коарсенинга или refinement.
- `DETMInfluence`:
  - `symbol_id: str`
  - `amplitude: float`
  - `phase: float | None`
  - `seed: int | None`
  - `mask/region: np.ndarray | tuple | None`
  - `duration/n_ticks: int | None`
  - `external_features: np.ndarray | dict[str, float] | None`
- Функция `apply_influence(state, influence)` входит в `step()`; влияет на поля детерминированно через переданный `rng`.
- Каталог символов (`symbols/` или `influences/`): `make_symbol(symbol_id, **params) -> DETMInfluence`, минимум 5–10 готовых шаблонов.

## Step API и время (промты 4.1–4.2)
- `step()` принимает `n_ticks: int` (tick‑driven). Внутренняя физическая шкала (`dt`) хранится в `config`, но наружный интерфейс оперирует тиками.
- `influence` может быть `None` (шаг без внешних воздействий).
- Возврат `observables` включает:
  - `signature` (короткая подпись сразу после шага);
  - `field_summaries` (минимальные статистики по полям);
  - `events` (опционально: локальные аномалии/аттракторы);
  - `cost` (оценка стоимости шага: время, операции, память).

## Диагностика (промты 5.1–5.2)
- `detm/runtime/diagnostics/attractors.py`: `detect_attractors(state) -> list[Attractor]` с полями `position/region`, `strength`, `stability_score`, `period_estimate`.
- `stability_metrics(state, history_window)` возвращает статус «прогресс падает/плато/колебания» по динамике `signature`.

## Профили исполнения (промты 6.1–6.2)
- В `observables.cost` фиксируются `cpu_time_ms`, `step_ops_estimate`, `memory_bytes_estimate`.
- Вводятся 2–3 «quality proxy» метрики на уровне DETM: `jitter_signature`, `oscillation_score`, `saturation_score`.

## Boundary / Ports (промт 7.1)
- `external_features` — вектор (`np.ndarray` или `dict[str, float]`) внутри `DETMInfluence`; DETM трактует как дополнительные параметры поля без знания источника (мышь/клава/датчик).

## Тестовый стенд (промты 8.1–8.2)
- `tools/headless_runner.py`: читает config, создаёт алфавит символов, гоняет `N` эпизодов, сохраняет `signatures/metrics` в `.npz/.jsonl`.
- Golden‑тесты: фиксированный `seed` + фиксированная последовательность `influence` → финальный `digest` совпадает с эталоном.

## Версионирование (промты 9.1–9.2)
- `schemas.py` содержит `DETM_CONFIG_V1`, `DETM_STATE_V1`, `DETM_SIGNATURE_V1`; `get_schema_versions()` возвращает их.
- При bump версии — `migrate_state(blob, from_version, to_version)` (пока stub + документация), чтобы сохранять совместимость.

## Runtime bridge (промты 10.1–10.2)
- `detm/integrations/runtime_bridge.py` предоставляет `DETMRuntimeBridge`:
  - `create_session(config, seed) -> session_id`
  - `session_step(session_id, influence, n_ticks) -> SessionStepResult(signature, observables, state_digest)`
  - `session_get_state_blob(session_id)`
- Без глобальных синглтонов: DETM должна поддерживать несколько одновременных сессий (или явный запрет). Рантайм-бридж организует изоляцию без UI/ComfyUI зависимостей.

## Watch Contract (artifact-first)

`watch_contract.jsonl` — канонический read-only projection packet (см. `detm/runtime/watch_contract.py`):
- связь с System Trace через `trace_ref`;
- ссылка на artifact через `outerfields_ref`;
- проекции `metrics.watchpoints` и `policy`.

`anti_goodhart` формализован как под-контракт в обоих местах:
- `policy.anti_goodhart`;
- `metrics.watchpoints.anti_goodhart`.

Нормализованные поля:
- `goodhart_flag: bool`;
- `target_signal: str`;
- `target_delta: float`;
- `degraded_signals: list[str]`;
- `degraded_signal_count: int`;
- `thresholds.target_signal: str`;
- `thresholds.min_target_delta: float`;
- `thresholds.min_degraded_signals: int`;
- `thresholds.degradation_epsilon: float`;
- `policy_reaction.apply: bool`;
- `policy_reaction.actions: list[str]`;
- `policy_reaction_enabled: bool`;
- `preferred_runtime_profile: str`;
- `runtime_profile_applied: bool`;
- `applicability: str`.

Flattened watchpoint поля для быстрых потребителей:
- `anti_goodhart_flag`;
- `anti_goodhart_degraded_signal_count`;
- `anti_goodhart_policy_reaction_applied`;
- `anti_goodhart_runtime_profile_applied`.

## Analytics read-model (app-layer, post-run)

Реализованный analytics слой не меняет канонический runtime API и не переводит DETM на direct DB writes.

Поддерживаемые entrypoints:
- `python main.py headless analytics ingest --run-dir <path>`
- `python main.py headless analytics summarize --run-dir <path>`
- `python main.py headless analytics query --db <path> --sql <query>`
- Python API: `ingest_run(run_dir)`, `summarize_run(run_dir)`, `open_run_db(run_dir)`

Derived outputs рядом с completed run:
- `analytics.sqlite`
- `analytics/run_summary.json`
- `analytics/event_windows.jsonl`
- `analytics/decision_windows.jsonl`
- `analytics/outerfields_index.jsonl`

Контракт этого слоя:
- raw artifact-first outputs (`trace/watch/contract/outerfields/state`) остаются source-of-truth;
- SQLite хранит summaries/refs/meta, а не dense arrays;
- ingest идемпотентен;
- результат должен честно маркироваться как `ok`, `partial` или `broken`.

## Multiscale bridge catalog (MSC-01, observe-only)

Текущий multiscale baseline не является runtime acceleration. Он строит derived multiscale readout поверх `step` events.

Зафиксированный интерфейс:
- `DETMConfig.multiscale_catalog`
- local bounded ring buffer в `detm.runtime.pattern_memory`
- bridge-shaped record scaffold:
  - `window_signature`
  - `interface_signature`
  - `horizon_k`
  - `forward_descriptor`
  - `reverse_descriptor_short`
  - `validity_envelope`
  - `db_refs`
- derived artifacts:
  - `multiscale_candidates.jsonl`
  - `scale_tension.jsonl`
  - `operator_catalog_hits.jsonl`

Observe-only semantics:
- canonical `DETMState` остаётся owned runtime/session;
- multiscale слой не делает `jump`, `refine`, `promote` или substitute execution;
- Redis не обязателен для completed run и не является source-of-truth;
- при наличии `redis_url` в артефакты и `config.json` уходит только safe endpoint без credentials.

## Transitional boundaries (не финальная архитектура)

Следующее нельзя трактовать как уже закрытую финальную архитектуру:
- `analytics.sqlite` не заменяет raw artifact-first слой;
- `multiscale_catalog` пока не является полноценным `Ln <-> Ln+1` executable bridge runtime;
- текущий `BridgeRecord` не хранит full forward/reverse trajectory bodies;
- Redis hot transport и trajectory store DB ещё не реализованы;
- particle/macronode semantics, `hint` execution и guarded `jump` остаются следующим отдельным этапом.

## Definition of Done (минимум для интеграции)
- Реализованы `reset/step/digest/serialize/deserialize`.
- Повторяемость: фиксированный `seed` → одинаковый результат.
- Типизированный `Influence` + библиотека символов.
- `Observables` возвращаются без UI.
- Есть headless runner и golden‑тесты.
- Версии схем зафиксированы и доступны через `get_schema_versions()`.


> Важно  
> EventBus и Scheduler являются **оркестрационными механизмами интеграции**.
>
> Они:
> - не задают физическое или модельное время;
> - не синхронизируют инварианты;
> - не имеют семантики завершения или подтверждения (ack).
>
> Глобальный тик является логической координатой,
> интерпретируемой коарсенером, а не Scheduler’ом.
Invariant ticks не являются «внутренним временем» объектов или инвариантов.
Они представляют собой точки наблюдения и активации
на выбранном уровне представления.
