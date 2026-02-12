# Единый источник концепций книги для DETM

Статус: интеграционная карточка (bridge doc).

Цель: перенести рабочие концепции из `docs/book/ru/` в документацию DETM в компактной форме, чтобы не объяснять их заново в каждом файле.

Правило использования:
- в новых документах давайте короткую ссылку на ID концепта (`C01`, `C02`, ...);
- подробную narrative-версию оставляем в книге;
- инженерную формулировку и критерии проверяемости держим здесь и в связанных карточках.

---

## C01. Уровень как окно времени

Определение:
уровень описания задаётся не названием, а окном времени, на котором инварианты различимы и воспроизводимы.

Опоры:
- `docs/rus/20_mechanisms/internal_time.md`
- `docs/rus/20_mechanisms/time_model_and_internal_spectra.md`
- `docs/book/ru/04_levels_as_time_windows.md`

---

## C02. Граница как оператор переноса

Определение:
граница не "стена", а интерфейс, через который проходят только совместимые с уровнем формы потока/сигнала.

Опоры:
- `docs/rus/20_mechanisms/contracts_as_flow_invariants.md`
- `docs/rus/40_hypotheses/boundary_interface_holography.md`
- `docs/book/ru/05_boundary_as_operator.md`

---

## C03. Контракт как инвариант потока

Определение:
контракт — устойчивое правило переноса через границу; живой контракт проверяется временем жизни и воспроизводимостью, а не декларацией.

Опоры:
- `docs/rus/20_mechanisms/contracts_as_flow_invariants.md`
- `docs/book/ru/06_contracts_as_flow_invariants.md`

---

## C04. Readout-панель вместо одной KPI

Определение:
метрика является наблюдаемым сигналом контура, а не целью сама по себе; измерение должно быть многоканальным и связным.

Опоры:
- `docs/rus/50_experiments/metrics.md`
- `docs/rus/30_architecture/OuterFields_and_Subscriptions.md`
- `docs/book/ru/12_kpi_by_maslow_and_levels.md`

---

## C05. Архитектурно нечестное = эксплойт интерпретатора

Определение:
улучшение датчика/отчёта без улучшения переноса и устойчивости считается дефектом архитектуры (Goodhart-режим).

Опоры:
- `docs/rus/90_notes/architecturally_unfair_interactions.md`
- `docs/rus/90_notes/readout_protocol_and_antigoodhart.md`
- `docs/book/ru/07_architecturally_unfair_and_antigoodhart.md`

---

## C06. Обучение как удержание класса состояния

Определение:
обучение трактуется как поиск стабилизирующих операторов, сохраняющих класс состояния под возмущением, а не как минимизация числовой ошибки.

Опоры:
- `docs/rus/90_notes/learning_model_detm.md`
- `docs/rus/30_architecture/global_tick.md`
- `docs/book/ru/09_brain_as_local_search.md`

---

## C07. Refine/Coarsen как тест адекватности уровня

Определение:
смена масштаба это не "оптимизация", а механизм проверки, способен ли текущий уровень корректно представлять динамику.

Опоры:
- `docs/rus/20_mechanisms/coarsening.md`
- `docs/rus/20_mechanisms/level_scaling_refinement.md`
- `docs/rus/30_architecture/Universal_Entry_via_Coarsen_Refine.md`

---

## C08. O(1)-оператор как компактный инвариант реакции

Определение:
после нормировки/коарсинга часть реакций описывается устойчивыми операторами с постоянной стоимостью шага в пределах области валидности.

Опоры:
- `docs/rus/90_notes/globaltime_o1_dt.md`
- `docs/rus/40_hypotheses/e_scale_boundary_invariants.md`

---

## C09. Наблюдатель как часть контура

Определение:
как только readout влияет на управление, измерение становится операцией, меняющей динамику; это нужно моделировать явно.

Опоры:
- `docs/rus/90_notes/variational_interpretation.md`
- `docs/rus/30_architecture/commit_protocol.md`
- `docs/book/ru/07_architecturally_unfair_and_antigoodhart.md`

---

## C10. Anti-capture как инвариант управляемости

Определение:
система устойчива к захвату, если власть не концентрируется в одном интерпретаторе метрик и есть процедура обратимого пересогласования контрактов.

Опоры:
- `docs/rus/90_notes/anti_capture_and_degeneracy.md`
- `docs/book/ru/25_anti_capture.md`

---

## Минимальный протокол против дублирования

1. В каждом новом тексте указывать ID концепта (`Cxx`) вместо повторного длинного объяснения.
2. Если нужна новая трактовка концепта, сначала обновлять этот файл, затем уже ссылаться на него.
3. Narrative-расширения писать в книге; операциональные формулировки и критерии — в `docs/rus`.
