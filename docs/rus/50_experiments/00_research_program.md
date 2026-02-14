# Research Program (DETM, RU)

Статус карточки:
- `status`: active (doc contract)
- `execution_status`: pending code contour (`F-01..F-03` в roadmap имеют статус `todo`)
- `last_reviewed`: `2026-02-14`

Этот файл фиксирует исследовательскую программу поверх существующих протоколов.

Назначение:
- связать гипотезы и эксперименты в единый контур;
- определить минимальный набор артефактов и критериев;
- снизить когнитивную нагрузку при планировании запусков.

Границы:
- этот документ не дублирует содержимое `exp_*`;
- детали процедур и формулы метрик остаются в исходных протоколах.

## Источники истины

- Гипотезы: `docs/rus/40_hypotheses/hypotheses.md`
- Общие метрики: `docs/rus/50_experiments/metrics.md`
- Базовые протоколы: `docs/rus/50_experiments/exp_*.md`
- Ограничения интерпретаций: `docs/rus/60_limits/limits.md`

## Матрица гипотез -> проверок

| Гипотеза | Основной протокол | Поддерживающий протокол | Ключевые метрики |
|---|---|---|---|
| H1, H4, H12 | `docs/rus/50_experiments/exp_phase_map.md` | `docs/rus/50_experiments/exp_object_masks.md` | `J_tail`, `curl_rms`, phase/stability |
| H2, H11, H17 | `docs/rus/50_experiments/exp_marker_scaling.md` | `docs/rus/50_experiments/exp_phase_map.md` | межмасштабная переносимость, drift метрик |
| H3, H8, H14 | `docs/rus/50_experiments/exp_transfer_speed.md` | `docs/rus/50_experiments/exp_channels.md` | lag-корреляции, доминирующие частоты, latency proxies |
| H5, H6 | `docs/rus/50_experiments/exp_gradient.md` | `docs/rus/50_experiments/exp_object_masks.md` | форма/период, дрейф, устойчивость к возмущениям |
| H7 | `docs/rus/50_experiments/exp_torus.md` | `docs/rus/50_experiments/exp_transfer_speed.md` | мобильность, сохранение формы и периода |
| H9 | `docs/rus/50_experiments/exp_channels.md` | `docs/rus/50_experiments/exp_transfer_speed.md` | отсутствие переноса без поддерживающей среды |
| H10 | `docs/rus/50_experiments/exp_density.md` | `docs/rus/50_experiments/exp_phase_map.md` | предел плотности инвариантов |
| H13, H15, H16 | `docs/rus/50_experiments/exp_phase_map.md` | `docs/rus/50_experiments/exp_object_masks.md` | PLV/спектр/потоки на границе, признаки сцепления |

## Минимальный пакет артефактов (для каждой серии)

1. `config`/`seed`/версии runtime (в metadata запуска).
2. Таймсерии компактных readout (`metrics.csv` или эквивалент).
3. Финальный слепок (`final_state.npz` или эквивалент).
4. Агрегат по серии (`summary`/таблица по seed и параметрам).

Дополнительно:
- хранить ссылку на конкретный протокол (`exp_*`) и целевые гипотезы (`H*`) в metadata.

## Критерии готовности гипотезы (DoD)

Гипотеза переводится в статус "поддержана в рамках модели", если:
1. Эффект воспроизводим на нескольких seed.
2. Эффект устойчив при умеренных вариациях параметров.
3. Есть сценарий фальсификации (и он явно описан в протоколе).
4. Артефакты позволяют независимый повтор без ручного восстановления контекста.

## Чего не делать в этом слое

- Не вводить новые физические интерпретации поверх readout.
- Не подменять критерий гипотезы "красивой" визуализацией.
- Не смешивать runtime-рефакторинг и исследовательский вывод в одном readout.
