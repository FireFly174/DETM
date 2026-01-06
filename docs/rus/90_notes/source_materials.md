# Исходные материалы и покрытие документацией

Папка `Discrete Emergent Medium with Multilevel Coarsening/` содержит исходные рассуждения («поток сознания»), из которых собирался канон проекта.
Цель этого файла — зафиксировать, **что уже перенесено в `docs/rus/`**, а что ещё требует оформления.

## 1) Принцип

- `docs/rus/` — каноническая документация (то, на что опирается код и эксперименты).
- исходная папка — источник контекста, идей и формулировок; она может содержать устаревшие/сырые фрагменты.

## 2) Карта соответствия (high level)

### Графовая формулировка (DAGM)
- Источник: `Discrete Emergent Medium with Multilevel Coarsening/Discrete Asynchronous Graph Model (DAGM).md`
- Канон: `docs/rus/10_model/dagm_core.md`

### Решёточная спецификация (DETM)
- Источники: `.../README.md`, `.../Дискретная энтропийно-временная модель (DETM).md`
- Канон: `docs/rus/10_model/model_core.md`

### Гипотезы
- Источник: `.../HYPOTHESES.md.md` (в т.ч. PLV/спектр/рациональные отношения частот)
- Канон: `docs/rus/30_hypotheses/hypotheses.md`
- Метрики для проверки: `docs/rus/40_experiments/metrics.md`

### Ограничения (limits)
- Источник: `.../LIMITS.md.md`
- Канон: `docs/rus/50_limits/limits.md`

### Коарсинг, уровни, шкала и нормировки
- Источники: `.../PROMT.md.md`, `.../Main holst.canvas`, `.../Экспериментальные данные.canvas`
- Канон: `docs/rus/20_mechanisms/coarsening.md`
- Дополнение (нормировка/шкала): `docs/rus/20_mechanisms/scale_axis.md`

### Параметры среды как поля (каналы/градиенты/«врезка»)
- Источники: `.../PROMT.md.md`, `.../Main holst.canvas`
- Канон: `docs/rus/20_mechanisms/channels.md`
- Дополнение: `docs/rus/20_mechanisms/parameter_fields.md`

### Метадокумент про риски/границы «модель vs интерпретация»
- Источник: `.../Анализ модели DETM и эмерджентной иерархии.md`
- Статус: полезно как справочная рамка; при необходимости перенести в `docs/rus/90_notes/` отдельной страницей.

## 3) Что явно вне канона DETM (но важно не потерять)

В исходниках есть блоки про уровни выше L0 и оркестрацию. Они вынесены в отдельные карточки `90_notes`:

- Fallback/subworld/pipeline swap: `docs/rus/90_notes/fallback_subworld.md`
- Форматы хранения нейронов/subworld и ресурсные критерии: `docs/rus/90_notes/storage_neurons_subworld.md`
- «Смысл», алфавиты уровней и LLM-mode: `docs/rus/90_notes/meaning_alphabet_llm_mode.md`
- Набросок системной архитектуры (термины): `docs/rus/90_notes/system_architecture_sketch.md`

Эти темы относятся к **уровням выше L0** и/или к оркестрации (ACGS), поэтому они не являются каноном L0 и не должны требоваться для работы `detm/runtime/api.py`.
