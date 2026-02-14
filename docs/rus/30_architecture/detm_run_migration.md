# detm.run Migration Guide

Обновлено: 2026-02-12

## Статус

- Compatibility слой `detm.run.*` удалён.
- Канонический orchestration API находится в `detm_app.*`.
- Пакет `detm` оставлен как библиотечное ядро (`detm.runtime`, `detm.core`, `detm.analysis`, `detm.metrics`, `detm.integrations`, `detm.presets`).

## Что использовать вместо detm.run

- `detm.run.DetmSession` -> `detm_app.runtime.session.DetmSession`
- `detm.run.EventBus` -> `detm_app.runtime.bus.EventBus`
- `detm.run.Event` -> `detm_app.runtime.bus.Event`
- `detm.run.EventHandler` -> `detm_app.runtime.bus.EventHandler`
- `detm.run.TickScheduler` -> `detm_app.runtime.scheduler.TickScheduler`
- `detm.run.TickRunner` -> `detm_app.runtime.scheduler.TickRunner`
- `detm.run.ScheduledItem` -> `detm_app.runtime.scheduler.ScheduledItem`
- `detm.run.InvariantCoarsener` -> `detm_app.runtime.coarsening.InvariantCoarsener`
- `detm.run.InvariantStreamSpec` -> `detm_app.runtime.coarsening.InvariantStreamSpec`
- `detm.run.parse_invariant_streams` -> `detm_app.runtime.coarsening.parse_invariant_streams`
- `detm.run.subscribers.*` -> `detm_app.runtime.subscribers.*`

## Рекомендуемый порядок миграции

1. Перевести все прямые импорты `detm.run.*` на `detm_app.*`.
2. Для CLI/UI/viz использовать только `detm_app.runner.headless`, `detm_app.ui.tk.runner`, `detm_app.ui.napari.subscriber`, `detm_app.transport`.
3. Проверить, что `pytest -q` проходит и в коде нет импортов `detm.run.*`.
