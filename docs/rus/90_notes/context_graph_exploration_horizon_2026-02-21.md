# Контекст как состояние и время исследуемости (2026-02-21)

Статус: инженерная фиксация review-выводов (внешний слой, без изменения канона L0).

## 1) Что подтверждено

1. В книге RU v2 уже есть формальный слой `state space / transitions / attractors`.
2. Введена декомпозиция состояния (`b/a/h/r/i/g/d`) и переход `x_{t+1} = F(x_t, e_t, pi_t)`.
3. Операционный цикл `симптом -> код -> шаг -> readout -> цена` описан как рабочий протокол.

Ссылки:
- `docs/book/ru_v2/_compiled_v2_print.md` (разделы про state space и diagnostic blank).

## 2) Обнаруженный зазор

В runtime/readout пока нет явной метрики "времени исследуемости" (сколько система удерживает управляемый режим до деградации обратной связи).

Это не противоречит канону, но ограничивает сравнение траекторий и anti-Goodhart контур в практических сценариях.

## 3) Предложение для code-contour

Добавить в watch/readout слой метрику:

- `exploration_horizon_ticks`

и сопутствующие поля:

1. `horizon_start_tick`
2. `horizon_break_reason` (`goodhart_flag`, `readout_degraded`, `boundary_stress`, `manual_stop`)
3. `horizon_recovery_cost_ticks`

## 4) Интеграционные точки

1. `detm/runtime/watch_contract.py` (snapshot/readout packet)
2. `detm_app/runtime/anti_goodhart.py` (детектор + причины срыва)
3. `detm/runtime/level_policy/model.py` (policy thresholds / window semantics)

## 5) Ограничение

Это операционный readout-слой. Канонические определения L0/инвариантов/времени не меняются.
