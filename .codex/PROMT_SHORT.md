# PROMT_SHORT — DETM Session Snapshot

Обновлено: 2026-02-14

Короткая точка входа перед задачей.
Полный контекст: `.codex/PROMT.md`.

---

## 1) Архитектура в 4 строках

- `detm/*` = library-core (L0 runtime + контракты).
- `detm_app/*` = orchestration/UI/transport.
- Канонический вход: `main.py`.
- Внешний доступ к runtime: artifact-first (`System Trace` + `Watch Trace` + `trace_ref`).

---

## 2) Текущая фаза (по roadmap)

- Baseline migration и fabric production-baseline закрыты.
- Главный открытый фокус: `WS-F` (обучение реакций в коде) + `WS-G-ND` (N-D контракты) + остаточный `WS-RT-MNT`.

Source-of-truth:
- `docs/rus/ROADMAP.md`
- `docs/rus/ROADMAP_HUMAN.md`

---

## 3) Запуск

- UI: `python main.py napari --interactive`
- Headless: `python main.py headless --help`
- Shell roles: `python main.py shell --help`

---

## 4) Мышление/дисциплина

- Уровень = окно времени (`L0..L5`).
- Граница = оператор переноса.
- Контракт = инвариант переноса.
- Обучение = удержание класса состояния под возмущением.
- Readout = панель сигналов, не одна KPI.

---

## 5) Триггер

Фраза `прочитай PROMT.md` = полный bootstrap:
1. фаза roadmap,
2. 3-5 приоритетов,
3. transition-зоны, которые нельзя закреплять как финальные.

Команда сохранена как совместимый alias, хотя prompt-layer теперь лежит в `.codex/`.
