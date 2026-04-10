# Синтез целевой архитектуры DETM

Статус: каноническая архитектурная сводка (рабочий ориентир для этапов roadmap A-G).  
Актуально на: 2026-02-10.

---

## 1. Что объединяет два варианта

Оба обсуждённых варианта описывают одну и ту же архитектуру в двух проекциях:

- Вариант A: инварианты системы (динамика первична, всё остальное — подписчики).
- Вариант B: операционная декомпозиция (какие контуры исполняют цикл, маршруты, хранение, наблюдение).

Итоговый синтез для DETM:
- `DETM Core` — источник истины о динамике;
- `Runtime/Orchestration` — исполняет цикл и политики, но не подменяет физику ядра;
- внешние контуры (`metrics/storage/viz/integrations`) работают как read-only подписчики через артефакты.

---

## 2. Канонические архитектурные инварианты

1. Динамика первична, наблюдатели вторичны.
2. `DETMState` имеет single-writer режим (пишет только runtime ядра).
3. Внешний доступ только artifact-first (`OuterFields/metrics/events/trace`), без прямого live-state API.
4. Уровень `Ln+1` видит `Ln` только через границу (`OuterFields`), а не через полный state.
5. Метрики и визуализация не управляют физикой динамики и могут быть отключены без ломки ядра.
6. Политики исполнения (`LevelPolicy`, частоты, окна, budgets) должны быть data-driven и воспроизводимыми.
7. Межнодовая синхронизация выполняется по `GlobalTick`/`commit boundary`, а не по внутренним microsteps.

---

## 3. Целевые слои (north star)

1. `DETM Core (L0)`  
Назначение: шаг динамики, состояние, бэкенды, обязательные инварианты и детерминизм.

2. `Runtime/Orchestration`  
Назначение: тик, scheduler, применение `LevelPolicy`, refine/correction контур, маршрутизация публикаций.

3. `DataBus + Artifacts`  
Назначение: publish/subscribe по типам данных (`outerfields`, `events`, `metrics`, `trace`, `preview(opt-in)`), контракт `trace_ref`.

4. `Observers` (read-only)  
Назначение: диагностика, метрики, storage, UI/napari/интеграции; без права писать в `DETMState`.

---

## 3.1 OOP-декомпозиция как инженерный принцип

Для runtime/fabric контура принимается объектная декомпозиция по ответственности
(в духе удачных паттернов из `D:\github\game\references\old_repo\lib`), но без копирования legacy-кода.

Минимальный профиль классов:

1. `Contract classes`  
   `CommitPacket`, `CommitTickRef`, `FabricEnvelope`, `ProofAck`, `TrustAck` — только схема/валидация/сериализация.
2. `Lifecycle classes`  
   `CommitChainManager` — последовательность `tail -> parent_ref`, проверка монотонности и целостности цепочки.
3. `Validation classes`  
   fabric/local validator-ы — проверка `proof/signature/epoch/watermark` + quorum policy (в т.ч. validator-set),
   без влияния на физику шага L0.
4. `Transport adapters`  
   pub/sub и node-to-node transport как отдельные адаптеры, заменяемые без изменения контрактов
   (MVP: `InMemoryFabricBus`, `TcpFabricTransport`/`TcpFabricRelay`).

Рабочий формат маркеров в коде (для контроля архитектурной глубины и техдолга):

- `ARCH-MARKERS: LAYER_BAND: Lx-Ly` — целевая полоса слоя.
- `ARCH-MARKERS: ABSTRACT_DISTANCE: N` — расстояние до нужной абстракции (`0` = контракт есть, `1+` = недостающие уровни).
- `ARCH-MARKERS: OOP_TECH_DEBT: ...` — конкретный долг по недостающему abstract/adapter/strategy.

Для текущего node/fabric трека целевая инженерная полоса: `L4-L5` (без углубления в специализированные `Ln>5` контуры).

Граница ответственности обязательна:

- Контрактные классы не знают о транспорте.
- Transport-адаптеры не знают физику L0.
- Validator-слой не меняет состояние ядра, только подтверждает/отклоняет артефакты.

---

## 4. Поток данных (типовой commit-цикл)

1. Вход: внешнее воздействие/команда попадает в runtime-контур.
2. Ядро делает шаг `state(t) -> state(t+1)` на выбранном backend.
3. Runtime применяет policy окна/частоты и формирует артефакты публикации.
4. `System Trace` фиксирует канонический журнал commit.
5. `Watch Trace` строится как проекция/watchpoints поверх `System Trace` и всегда содержит `trace_ref`.
6. Подписчики читают артефакты и не влияют на шаг ядра напрямую.
7. Для node/fabric контура commit-артефакты синхронизируются через `epoch/watermark` координатора, без hard-barrier внутри шага ядра.

---

## 5. Что не должно попадать в L0 Core

- UI и визуализация;
- KPI-оптимизация;
- прикладная бизнес-логика решений;
- тяжёлая аналитика/offline-пайплайны;
- оркестрация подписок и storage policy.

Примечание:
контуры обучения реакций (roadmap этап F) допустимы только как внешний/надъядерный runtime-механизм, а не как часть шага L0.

---

## 6. Привязка к текущему репозиторию (`as-is: 2026-02-13`)

- orchestration закреплён в `detm_app/runtime/*` (`session`, `scheduler`, `bus`, `subscribers`); legacy `detm/run/*` удалён.
- `detm/runtime/*` остаётся библиотечным ядром (L0 API, backends, state, serialization, `OuterFields`, fabric runtime).
- UI/viz контур закреплён в `detm_app/ui/*` и `detm_app/transport/*` как read-only consumers артефактов/сериализованного state.
- launcher-граница единая: `main.py` (`napari`/`headless`/`shell`), с явным разделением launcher-help и full headless help.

---

## 7. Привязка к roadmap

- Этап A: выделение `detm_app` и границы библиотека/приложение.
- Этап B: `LevelPolicy` как data-driven runtime-контур (+ observability profiles).
- Этап D: `PatternStore/PatternCache` + pruning по `error/deviation`.
- Этап E: `System Trace`/`Watch Trace`, `trace_ref`, policy хранения `L0..Ln`, canonical napari path.
- Этап G: node/fabric commit-протокол (`CommitPacket`, `State/Boundary/Coarsened/Proof commits`), синхронизация по `GlobalTick` и `local-first + validation-sync`.

---

## 8. Связанные документы

- `docs/rus/ROADMAP.md`
- `docs/rus/30_architecture/runtime_api.md`
- `docs/rus/30_architecture/global_tick.md`
- `docs/rus/30_architecture/OuterFields_and_Subscriptions.md`
- `docs/rus/30_architecture/commit_protocol.md`
- `docs/rus/30_architecture/Level_policy_schema.md`
