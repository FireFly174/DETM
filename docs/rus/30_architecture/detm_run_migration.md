# detm.run Migration Guide

Обновлено: 2026-02-12

## Статус

- `detm.run.*` оставлен только как compatibility facade.
- facade работает в lazy-режиме и выдаёт `DeprecationWarning` при первом доступе к каждому символу.
- целевой дедлайн удаления facade: версия `0.3.0` (плановая дата `2026-06-30`).

## Что использовать вместо detm.run

- `detm.run.DetmSession` -> `detm_app.session.DetmSession`
- `detm.run.EventBus` -> `detm_app.bus.EventBus`
- `detm.run.Event` -> `detm_app.bus.Event`
- `detm.run.EventHandler` -> `detm_app.bus.EventHandler`
- `detm.run.TickScheduler` -> `detm_app.scheduler.TickScheduler`
- `detm.run.TickRunner` -> `detm_app.scheduler.TickRunner`
- `detm.run.ScheduledItem` -> `detm_app.scheduler.ScheduledItem`
- `detm.run.InvariantCoarsener` -> `detm_app.coarsening.InvariantCoarsener`
- `detm.run.InvariantStreamSpec` -> `detm_app.coarsening.InvariantStreamSpec`
- `detm.run.parse_invariant_streams` -> `detm_app.coarsening.parse_invariant_streams`
- `detm.run.subscribers.*` -> `detm_app.subscribers.*`

## Рекомендуемый порядок миграции

1. Перевести все прямые импорты `detm.run.*` на `detm_app.*`.
2. Запустить тесты/смоук-сценарии CLI/UI.
3. Убедиться, что CI-проверка `tests/test_no_detm_run_imports.py` проходит (она блокирует новые импорты `detm.run.*`).
4. После полного перехода удалить facade в релизе `0.3.0`.

## Примечание для backward compatibility

До удаления facade обратная совместимость сохраняется, но `DeprecationWarning`
считается нормой и сигналом к миграции.
