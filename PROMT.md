# DETM — Canonical Bootstrap Prompt (`PROMT.md`)

Обновлено: 2026-02-14  
Статус: источник стартового контекста для рабочих сессий.

Этот файл задает исходную точку мышления и исполнения задач в DETM.
Он не дублирует всю теорию из книги и карточек, а фиксирует рабочий минимум:
канон, фазу roadmap, ограничения и ближайшие приоритеты.

---

## 1) Команда bootstrap

Фраза пользователя:
- `прочитай PROMT.md`

означает:
1. восстановить контекст по prompt-stack (`SYSTEM_PROMT_DETM_CREATIVE.md` + этот файл + `docs/rus/ROADMAP.md` + опорные карточки),
2. отделить `as-is` от `to-be`,
3. дать короткий запускной ответ:
   - текущая фаза roadmap,
   - 3-5 ближайших приоритетов,
   - переходные части, которые нельзя закреплять как финальные.

---

## 2) Что считается каноном (не переопределяется в обычной задаче)

1. `detm/*` — library-core (L0 runtime + контракты).
2. `detm_app/*` — orchestration/UI/transport/app-layer.
3. L0 runtime UI-агностичен; внешний доступ artifact-first.
4. `System Trace` канонический; `Watch Trace` проекционный, с обязательным `trace_ref`.
5. Любая задача оценивается вопросом: приближает к target-архитектуре или закрепляет transition.
6. Обучение в DETM: удержание инварианта под возмущением, а не оптимизация одной KPI.
7. Anti-Goodhart обязателен: readout-панель, а не одиночная метрика.

Подробные основания:
- `docs/rus/90_notes/book_concepts_single_source.md`
- `docs/rus/90_notes/learning_model_detm.md`
- `docs/rus/90_notes/readout_protocol_and_antigoodhart.md`

---

## 3) As-Is (текущий кодовый контур)

- Канонический вход: `python main.py`.
- Основной UI путь: `python main.py napari --interactive`.
- Headless/experiment путь: `python main.py headless ...`.
- Fabric baseline и app-layer migration завершены на baseline уровне.
- `detm.py` legacy-обертка удалена; единственный canonical launcher — `main.py`.

Текущий статус задач и зависимостей всегда смотреть в:
- `docs/rus/ROADMAP.md` (source-of-truth)
- `docs/rus/ROADMAP_HUMAN.md` (короткий обзор)

---

## 4) To-Be (архитектурный вектор)

North star задан документами:
- `docs/rus/ROADMAP.md`
- `docs/rus/90_notes/codebase_spec_2026-02-09.md`
- `docs/rus/90_notes/architecture_variants_l0_and_fabric_2026-02-09.md`

Ключевые незакрытые направления:
1. `WS-F`: контур обучения реакций в коде (operators, transferability, anti-Goodhart runtime path).
2. `WS-G-ND`: эволюция state/runtime контрактов к shape[N].
3. `WS-RT-MNT`: остаточный structural debt в крупных runtime/app модулях.

---

## 5) Рабочие ограничения

Запрещено:
- подменять улучшение динамики улучшением отчета;
- доказывать успех одной метрикой;
- фиксировать переходные решения как финальные без явного решения roadmap.

Обязательно:
- отделять факт / гипотезу / допущение;
- указывать границы применимости;
- оставлять проверяемый readout и тестовый след (когда это применимо).

---

## 6) Быстрый формат ответа в сессии

Для нетривиальной задачи:
1. Контекст (фаза roadmap + актуальные ограничения)
2. Инварианты (что нельзя ломать)
3. Выбранный шаг (и почему)
4. Readout/проверка
5. Следующий минимальный шаг

---

## 7) Prompt Stack (кратко)

База:
- `SYSTEM_PROMT_DETM_CREATIVE.md`
- `PROMT.md`
- `docs/rus/ROADMAP.md`
- `docs/rus/ROADMAP_HUMAN.md`
- `docs/rus/90_notes/book_concepts_single_source.md`
- `docs/rus/90_notes/learning_model_detm.md`
- `docs/rus/90_notes/readout_protocol_and_antigoodhart.md`

Расширение (по необходимости):
- `docs/rus/40_hypotheses/hypotheses.md`
- `docs/rus/90_notes/codebase_spec_2026-02-09.md`
- `docs/rus/90_notes/architecture_variants_l0_and_fabric_2026-02-09.md`

---

## 8) Итоговый контрольный вопрос

Перед любым merge/change:

> Это изменение усиливает канон и движение к target-архитектуре,
> или просто делает переходный путь более "удобным" и закрепляет его?
