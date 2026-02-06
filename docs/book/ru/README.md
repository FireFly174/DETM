# Книга: рабочая концепция (RU)

Статус: черновик / рабочий контур.

Эта папка — отдельное пространство под “книгу”: сборка идей в линейный нарратив.
Она **не является каноном DETM** и не должна менять определения/контракты L0-модели.

Цели:
- собрать “единую картину” (уровни, границы, контракты, метрики) в читаемую архитектуру;
- сохранить терминологию (без пафоса, но с инженерной строгостью);
- иметь место для оглавления, глав и связей с каноном `docs/rus/`.

Точки опоры в каноне:
- контракты/границы/перенос: `docs/rus/20_mechanisms/contracts_as_flow_invariants.md`
- видимые метрики и анти‑артефакты: `docs/rus/50_experiments/metrics.md`
- анти‑Goodhart / “архитектурно нечестное”: `docs/rus/90_notes/architecturally_unfair_interactions.md`
- anti‑capture: `docs/rus/90_notes/anti_capture_and_degeneracy.md`
- межкомпанийнный пул задач: `docs/rus/90_notes/intercompany_level_sync_task_pool.md`

С чего начать в книге:
- оглавление: `docs/book/ru/00_outline.md`
- словарь терминов: `docs/book/ru/01_terms.md`
- assets (картинки/мемы): `docs/book/ru/assets.md`
- пролог (тон и задача): `docs/book/ru/08_prologue_how_not_to.md`
- сборка в один документ: `python tools/compile_book_ru.py`
- быстрый запуск сборки (Windows): `tools\\compile_book_ru.cmd [draft|print]`

Сборка (по умолчанию пишет `docs/book/ru/_compiled.md`):
- быстрый запуск (Windows): `tools\\compile_book_ru.cmd [draft|print]`
- черновик (с заметками автора): `python tools/compile_book_ru.py --mode draft`
- «печать» (без заметок/комментариев): `python tools/compile_book_ru.py --mode print`
- отчёт по объёму глав (для калибровки «где разжевать»): `python tools/compile_book_ru.py --report-only`

Заметки автора (не для печати):
- Блоки заметок: `<!-- @draft-begin -->` … `<!-- @draft-end -->` (в режиме `print` полностью вырезаются).
- Комментарии/подсказки (admonitions): строки вида `> [!NOTE]` / `> [!TIP]` / `> [!IMPORTANT]` / `> [!WARNING]` / `> [!CAUTION]`
  (в режиме `print` вырезаются целиком вместе с цитатным блоком).

Порядок глав задаётся в `docs/book/ru/manifest_ru.txt`.

Если среда запрещает запись в файл, используйте вывод в stdout и редирект:
`python tools/compile_book_ru.py --mode draft --out - > docs/book/ru/_compiled.md`

Черновые главы (по порядку):
- Пролог:
  - «Как не надо»: `docs/book/ru/08_prologue_how_not_to.md`
- Минимальная онтология уровней:
  - L0: "есть/нет": `docs/book/ru/02_l0_exists.md`
  - L1: минимальная операция: `docs/book/ru/03_l1_minimal_operation.md`
  - Уровни как окна времени: `docs/book/ru/04_levels_as_time_windows.md`
- Границы и смысл:
  - Граница как оператор переноса: `docs/book/ru/05_boundary_as_operator.md`
  - Контракты как инварианты потоков: `docs/book/ru/06_contracts_as_flow_invariants.md`
  - "Архитектурно нечестное" и anti-Goodhart: `docs/book/ru/07_architecturally_unfair_and_antigoodhart.md`
- Маслоу как 3D‑конструкт: `docs/book/ru/10_maslow_3d.md`
- KPI по Маслоу: иерархия метрик: `docs/book/ru/12_kpi_by_maslow_and_levels.md`
- Цели, совместимые с жизнью: границы вместо запретов: `docs/book/ru/13_life_compatible_goals.md`
- Индивид, коллектив, ИИ:
  - Мозг как локальный перебор: `docs/book/ru/09_brain_as_local_search.md`
  - Коллектив как greedy-поиск: `docs/book/ru/10_collective_as_greedy_search.md`
  - Нейросети и "нет L0": `docs/book/ru/11_neural_nets_and_missing_l0.md`
- Система уровней и карьеры: `docs/book/ru/20_career_levels_system.md`
- Инженер интерфейса «человек ↔ система»: перевод языка уровней: `docs/book/ru/21_interface_engineer_translation.md`
- «Пансионат»: закрытый базис и честная обратная связь: `docs/book/ru/26_pensionat_and_honest_feedback.md`
- Форум идей: анонимная подача и ИИ‑интерфейс: `docs/book/ru/27_forum_of_ideas_and_ai_interface.md`
- «Реальный МРОТ» и окупаемость базиса: `docs/book/ru/28_real_mrot_and_payback.md`
- Кейс: Valve как прототип «рынка проектов»: `docs/book/ru/29_valve_as_prototype.md`
- Anti-capture (отдельная глава): `docs/book/ru/25_anti_capture.md`
- Межкомпанийнный рынок задач: `docs/book/ru/30_intercompany_task_market.md`
- Динамическая цена задач (aging): `docs/book/ru/31_dynamic_task_pricing.md`
- Баланс мощностей: бригадир как диспетчер очереди: `docs/book/ru/32_capacity_matching_and_dispatch.md`
- Самоинтерпретируемая задача (паспорт/спека): `docs/book/ru/33_self_interpreting_task_spec.md`
- Конечный ресурс и «фиктивная бесконечность»: `docs/book/ru/35_finite_resources_and_fake_infinity.md`
- Протокол “нужно”, а не “хотим”: `docs/book/ru/40_global_needs_protocol.md`
