# DETM Codebase Specification (2026-02-09)

Статус: рабочая техническая спецификация (snapshot).

---

## 1. Scope

DETM в текущем состоянии — Python-пакет `detm` с runtime L0, headless runner, UI/viz, интеграциями и тестами.

Единица поставки:
- пакет `detm` (см. `pyproject.toml`);
- скриптовые entrypoints через `main.py` и `main.py`.

---

## 2. Platform & Dependencies

### 2.1 Runtime Platform

- Python: `>=3.12`
- OS: кроссплатформенно (проверяемый локальный стенд: Windows)

### 2.2 Mandatory Dependencies

- `numpy>=1.26`
- `msgpack>=1.0`

### 2.3 Optional Dependencies

- `torch` (опциональный backend)

### 2.4 Standard Library Usage (ключевое)

- `argparse`, `json`, `pathlib`, `dataclasses`, `socket`, `threading`, `tkinter` и др.

---

## 3. Package Topology

### 3.1 Core Math Layer (`detm/core`)

Назначение:
- дискретная динамика поля;
- вычисление энтропийного подавления;
- базовые инварианты шага.

Модули:
- `detm/core/fields.py`
- `detm/core/entropy.py`
- `detm/core/invariants.py`

Библиотеки:
- `numpy` (и тензоры backend через runtime)

### 3.2 Runtime API Layer (`detm_app/runtimetime`)

Назначение:
- канонический публичный API L0;
- состояние, конфиг, сериализация, сигнатуры;
- backend-абстракция (`numpy`/`torch`);
- diagnostics и `OuterFields`-артефакты.

Ключевые модули:
- `detm_app/runtimetime/api/*`
- `detm_app/runtimetime/state.py`
- `detm_app/runtimetime/config/*`
- `detm_app/runtimetime/influence/*`
- `detm_app/runtimetime/serialization/__init__.py`
- `detm_app/runtimetime/signature.py`
- `detm_app/runtimetime/outerfields.py`
- `detm_app/runtimetime/backends/{numpy_backend.py, torch_backend.py}`

Публичный контракт (`detm/__init__.py`):
- типы: `DETMConfig`, `DETMInfluence`, `DETMState`, `DETMSignature`, `FieldSummaries`, `Observables`
- функции: `reset`, `step`, `digest`, `serialize`, `deserialize`, `get_schema_versions`

Библиотеки:
- `numpy`, `msgpack`, опционально `torch`

### 3.3 Run/Orchestration Layer (`detm_app/runtime`)

Назначение:
- сессионная обёртка над runtime API;
- событийная шина;
- tick-scheduler;
- coarsening streams;
- подписчики записи артефактов и стриминга.

Ключевые модули:
- `detm_app/runtime/session.py` (`DetmSession`)
- `detm_app/runtime/bus.py` (`EventBus`)
- `detm_app/runtime/scheduler.py` (`TickScheduler`, `TickRunner`)
- `detm_app/runtime/coarsening.py` (`InvariantCoarsener`)
- `detm_app/runtime/subscribers/__init__.py`

Примечание по архитектуре:
- отдельный пакет `detm_app/` отсутствует;
- orchestration сейчас реализован внутри `detm_app/runtime/*`.

### 3.4 Metrics & Analysis (`detm/metrics`, `detm/analysis`)

Назначение:
- вычисление наблюдаемых метрик и диагностик вне ядра динамики.

Ключевые модули:
- `detm/metrics/base.py`
- `detm/metrics/builtin.py`
- `detm/metrics/boundary_flux.py`
- `detm/analysis/{fields.py, boundary_flux.py, grid_timeseries.py}`

### 3.5 Integration Layer (`detm/integrations`)

Назначение:
- адаптеры DETM для внешних систем.

Ключевые модули:
- `detm/integrations/runtime_bridge.py`
- `detm/integrations/acgs_backend.py` (`ACGSDetmBackend`)

### 3.6 UI/Viz Layer (`detm_app/ui`, `detm_app/transport`)

Назначение:
- локальный UI для запуска;
- визуализационный daemon/transport/protocol.

Ключевые модули:
- `detm_app/ui/tk_runner.py`
- `detm_app/transport/{daemon.py, protocol.py, transport.py, tk_panel.py, subscriber.py}`

Библиотеки:
- stdlib `tkinter`, `socket`, `threading`

### 3.7 Napari Migration Track (архитектурный статус)

#### 3.7.1 Реализовано сейчас

- Рабочий UI-контур: `Tk` (`detm_app/ui/tk_runner.py`).
- Рабочий viz transport:
  - `embedded` рендер (в том же процессе),
  - `tcp` через headless hub (`detm_app/transport/daemon.py`, `detm_app/transport/transport.py`).
- `VizStreamer` публикует сериализованные state blobs по подписке.

#### 3.7.2 Прототипы / следы миграции

- legacy wrappers `detm_napari_viewer.py`/`detm_napari_lab.py` удалены;
  канонический запуск napari идёт через `python main.py napari ...`.
- В notes зафиксирован целевой UX-вектор:
  - `docs/rus/90_notes/DETM_solution_passport_filled.md`
  - `docs/rus/90_notes/solution_passport.md`
  - `docs/rus/30_architecture/Universal_Entry_via_Coarsen_Refine.md`

#### 3.7.3 Целевое архитектурное требование (из notes)

- `napari/ComfyUI` должны работать как **read-only подписчики**;
- L0 runtime остаётся UI-агностичным;
- публикация наружу — через артефакты/контракты (`OuterFields`, metrics, events),
  а не через прямой доступ к внутреннему `DETMState`.

#### 3.7.4 Фактический статус

- Migration to napari: **частично** (прототип есть, канонической интеграции нет).
- Production path today: **Tk + TCP/embedded viz**.

---

## 4. Entry Points

### 4.1 Interactive Launcher

- `main.py`
- режим по умолчанию: UI
- fallback к headless CLI при non-`ui` аргументах

### 4.2 Headless CLI

- `main.py`
- поддерживает presets/config overrides, batch runs, traces, viz streaming, invariant streams

---

## 5. Data & Artifact Formats

### 5.1 State Serialization

Формат:
- metadata через `msgpack`
- dense arrays через вложенный `npz` payload (compressed)

Модуль:
- `detm_app/runtimetime/serialization/__init__.py`

### 5.2 Run Artifacts (headless)

Типовые файлы:
- `config.json`
- `state.msgpack`
- `digest.json`
- `history.jsonl`
- `trace.jsonl`
- `fields_hist.npz` (опционально)
- `invariants.jsonl` (опционально)
- `catalog.json` (batch root)

---

## 6. Test Specification Snapshot

Команда:
- `pytest -q`

Результат на 2026-02-09:
- `19 passed, 1 skipped`

Покрываемые контуры (по названиям тестов):
- интеграционный контракт runtime
- инварианты энергии/энтропии
- coarsening
- влияние (`influence`)
- parity numpy/torch
- ACGS backend adapter

Каталог:
- `tests/`

---

## 7. Roadmap Mapping (Code Reality)

Фактический этап:
- между фазами 2 и 3 (`docs/rus/ROADMAP.md`).

Статус:
- Фаза 1: выполнено (ядро и API стабильны)
- Фаза 2: частично (есть session/scheduler/bus, но нет выделенного `detm_app`)
- Фаза 3: частично (LevelPolicy формализован в доке, не реализован как центральный runtime-контур)
- Фазы 4–7: не реализованы как полноценные code-contours

Дополнение по фазе 6 (UI/analyzers):
- текущая рабочая ветка визуализации: Tk/TCP;
- napari — зафиксированный архитектурный трек, но не основной интеграционный путь на текущем snapshot.

---

## 8. Non-Goals (Current Snapshot)

- нет claim о физически достоверной симуляции атомных систем;
- нет реализованного обучения операторов/навыков в runtime;
- нет полноценного refinement-контура в коде `detm`.

---

## 9. Архитектурный синтез (из обсуждений, с учётом текущего кода)

Этот раздел фиксирует, как использовать предложенные вами схемы
без копирования их 1-в-1.

### 9.1 Что принимается как рабочий принцип уже сейчас

- `L0` как единственный постоянно тикающий слой динамики.
- `Ln` как слои интерпретации/агрегации, а не отдельные “физические миры”.
- Внешний контур должен читать артефакты (`OuterFields/metrics/events`), а не прямой `DETMState`.
- GPU-first направление: состояние и шаги динамики стремятся оставаться на GPU.

Это согласовано с текущим runtime и каноном:
- `detm_app/runtimetime/api/*`
- `detm_app/runtimetime/outerfields.py`
- `docs/rus/30_architecture/OuterFields_and_Subscriptions.md`

### 9.2 Что трактуется как target-архитектура (ещё не реализовано)

- “SSD библиотека инвариантов/паттернов” как постоянное хранилище операторов.
- Явный RAM-cache недавних паттернов/операторов уровня.
- Полностью децентрализованная fabric-сеть узлов без центрального runtime.
- Полный lifecycle `predict -> refine -> collapse -> persist` на уровне `NodeRuntime`.

Сейчас это находится на уровне design/hypothesis и roadmap,
а не на уровне готового code-contour.

### 9.3 Как интерпретировать две предложенные версии

Версия 1 (“L0 поток + подписчики”) принимается как
ближайшая системная модель для фаз 2-5:
- хорошо ложится на `Session/Bus/Scheduler`;
- совместима с `OuterFields` и read-only подписками;
- напрямую переводится в `LevelPolicy + refinement + reactions`.

Версия 2 (“децентрализованная сеть узлов”) принимается как
дальняя модель для фаз 6-7+:
- требует отдельного `Fabric/Protocol`;
- требует формализации межузлового контракта поверх `OuterFields`;
- не должна подменять текущий single-runtime контур до завершения фазы 3/4.

Отдельная фиксация исходных рассуждений:
- `docs/rus/90_notes/architecture_variants_l0_and_fabric_2026-02-09.md`

### 9.4 Нормализованная формула DETM для спецификации

Операционный слой (as-is / near-term):

`L0(t+1) = F(L0(t), influence_t) + Sum_i feedback_i(t)`

`Ln_i(t+1) = G_i(project_i(L0(t)), local_state_i(t))`

Сетевой слой (to-be / research):

`Node_j: state_j(t+1) = H_j(state_j(t), OuterFields_in_j(t))`

`publish_j -> OuterFields_out_j(t)`

`Fabric routes OuterFields_out_j -> subscribers`

### 9.5 Ограничения на перенос идей в код

- Не вводить “глобальную децентрализацию” раньше завершения `LevelPolicy`.
- Не объявлять SSD/RAM-память паттернов реализованной, пока нет явного storage API.
- Не смешивать канон runtime API с исследовательскими метафорами.
- Любой новый уровень обязан оставаться совместимым с `OuterFields`-контрактом и commit-границами.

### 9.6 Минимальный практический next step (для фиксации в коде)

1. Ввести интерфейс `PatternStore` (пока локальный file-backed stub).
2. Ввести `PatternCache` в рантайме (LRU по сигнатурам/инвариантам).
3. Подключить cache lookup в контур coarsening/reaction до полного refinement.
4. Оставить transport-node/fabric как отдельный этап после стабилизации п.1-3.



