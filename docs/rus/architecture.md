# Архитектура DETM (RU)

Этот документ фиксирует *текущее* состояние архитектуры и интерфейсов интеграции DETM.
Он соответствует английской версии `docs/eng/architecture.md`.

DETM — это **чистая L0‑динамика**. Она не знает про Scheduler/ComfyUI/UI.
Внешние системы взаимодействуют с ней через контракт runtime API и наблюдаемые величины.

```mermaid
flowchart LR
  UI[UI/CLI] --> Runner[TickRunner]
  Runner --> Session[DetmSession (L0)]
  Runner --> Bus[EventBus]
  Bus --> Sub1[Trace/History subscribers]
  Bus --> Sub2[Diagnostics/Invariant subscribers]
  Bus --> Viz[Viz subscriber]
  Viz -->|embedded| Canvas[Canvas/Panel]
  Viz -->|tcp| Daemon[TCP daemon] --> Viewer[Viewer/Panel]
```

---

## 1) Runtime Contract (L0 API)

Канонический API: `detm/runtime/api.py`:

- `reset(config: DETMConfig, seed: int) -> DETMState`
- `step(state: DETMState, influence: DETMInfluence | None, n_ticks: int, rng: np.random.Generator | None = None) -> (DETMState, Observables)`
- `digest(state: DETMState) -> DETMSignature`
- `serialize_state(state: DETMState) -> bytes`
- `deserialize_state(blob: bytes) -> DETMState`
- `get_schema_versions() -> dict[str, str]`

Важно:
- `n_ticks` — **целое число тиков** (tick-driven модель времени).
- детерминизм: все стохастические операции используют `rng` или `state.rng_state`.
- `step()` возвращает **observables** без зависимости от UI.

---

## 2) Бэкенды (Torch/Numpy) и представление состояния

Вычислительные бэкенды: `detm/runtime/backends/`:
- `TorchBackend` (CPU/CUDA, опциональная зависимость)
- `NumpyBackend` (эталон + фолбэк)

Правило: **бэкенд не конвертирует состояние**.
Он только делает шаг в той репрезентации, которая уже есть в `DETMState`:
- tensor-state → tensor-state (TorchBackend)
- numpy-state → numpy-state (NumpyBackend)

---

## 3) Influence API (“алфавит”)

`DETMInfluence` — внешний порт воздействия на L0.
Библиотека символов: `detm/runtime/symbols.py`:
- `make_symbol(symbol_id, **params) -> DETMInfluence`
- `list_symbols() -> list[str]`

Применение влияния: `detm/runtime/influence.py`:
- `apply_influence(field_state, influence, rng) -> InfluenceApplication`

`external_features` — общий вектор/словарь параметров без знания источника (мышь/клава/датчик).

---

## 4) EventBus, подписчики, Scheduler и invariant ticks

`detm/run/bus.py`: минимальный синхронный EventBus для подключения:
- логгеров/трейсов
- сериализации артефактов
- виз-стриминга
- invariant tick streams (коарсинг-таймкиперы)
- внешних слушателей (ACGS может подключать свои)

Scheduler: `detm/run/scheduler.py`:
- `TickScheduler` публикует `tick`/`signal`
- `TickRunner` связывает `DetmSession` и Scheduler

Семантика `TickRunner`:
1) на глобальном тике применяет все due‑влияния **без продвижения времени**
2) делает ровно **1** L0‑тик

Invariant ticks: `detm/run/coarsening.py`:
- потоки задаются рациональным dt относительно L0 (например `1/10`, `4/25`)
- коарсенер **не накапливает** значения, только эмитит `invariant_tick`
- сохранение/JSON — отдельные подписчики

---

## 5) Entrypoints и единый конфиг

`python main.py`:
- по умолчанию открывает UI
- использует локальный `config.example.py` (если нет — копирует из `detm/presets/config.default.py`)

Headless CLI: `detm/cli.py`:
- одиночный прогон и batch
- опциональный viz streaming

---

## 6) Визуализация: embedded vs TCP

Визуализация — это **подписчик/потребитель** кадров состояния, а не часть L0.

Режимы:
1) `embedded`: рендер в том же процессе (без сокетов)
2) `tcp`: DETM шлёт state blobs в headless‑daemon, а UI подписывается и рендерит

TCP daemon: `detm/viz/daemon.py` (headless hub):
- producer: `{type:\"state\", ...}`
- viewer: `{type:\"subscribe\"}` → поток `state` сообщений
