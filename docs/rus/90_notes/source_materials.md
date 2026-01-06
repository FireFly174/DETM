# Исходные материалы и покрытие документацией

Изначально большая часть идей и формулировок велась как «поток заметок» (Markdown + Obsidian `.canvas`).
Эти исходники рассматриваются как **локальное сырьё** и **не трекаются git** (их можно хранить рядом с репозиторием или в локальной папке `docs/source/`, которая игнорируется).

Цель этого файла — зафиксировать, где находится канон, и какие темы из исходников уже перенесены в структуру `docs/rus/` (и переведены в `docs/eng/`).

---

## 1) Принцип

- `docs/rus/` — каноническая документация (на неё опираются код и эксперименты).
- `docs/eng/` — перевод (может быть неполным/упрощённым).
- исходные заметки и выгрузки из `.canvas` — вспомогательный материал и не являются частью канона.

Если нужно локально «распаковать» текстовые узлы `.canvas` в карточки, используйте `tools/extract_canvas_cards.py` (выходные файлы считаются локальными и не коммитятся).

---

## 2) Покрытие каноном (где что лежит)

- DAGM (графовая формулировка): `docs/rus/10_model/dagm_core.md`
- DETM (решёточная спецификация): `docs/rus/10_model/model_core.md`
- Механизмы: `docs/rus/20_mechanisms/*`
  - внутреннее время/асинхронность: `docs/rus/20_mechanisms/internal_time.md`
  - параметры среды как поля: `docs/rus/20_mechanisms/parameter_fields.md`
  - коарсинг/шкалы: `docs/rus/20_mechanisms/coarsening.md`, `docs/rus/20_mechanisms/scale_axis.md`
- Гипотезы (список): `docs/rus/30_hypotheses/hypotheses.md`
- Эксперименты и метрики: `docs/rus/40_experiments/*`
  - метрики: `docs/rus/40_experiments/metrics.md`
  - фазовые карты режимов: `docs/rus/40_experiments/exp_phase_map.md`
  - маски/границы объектов: `docs/rus/40_experiments/exp_object_masks.md`
  - скорость переноса/лаги: `docs/rus/40_experiments/exp_transfer_speed.md`
- Ограничения (limits): `docs/rus/50_limits/limits.md`

---

## 3) Карточки‑расширения (выжимка из canvas)

Следующие темы из исходных `.canvas` перенесены как отдельные карточки/протоколы:

- аттракторы как «объекты»: `docs/rus/30_hypotheses/attractors_as_objects.md`
- граница как интерфейс и «голографичность»: `docs/rus/30_hypotheses/boundary_interface_holography.md`
- инерция/«масса» из локальности: `docs/rus/30_hypotheses/inertia_mass_locality.md`
- вихри как квазичастицы: `docs/rus/30_hypotheses/vortices_quasiparticles.md`
- ёмкость уровня и фазовые переходы: `docs/rus/30_hypotheses/level_capacity_phase_transitions.md`

---

## 4) Что явно вне канона L0 (но важно не потерять)

Темы про уровни выше L0 и/или оркестрацию (ACGS) хранятся в `90_notes`:

- fallback/subworld: `docs/rus/90_notes/fallback_subworld.md`
- форматы хранения нейронов/subworld и ресурсные критерии: `docs/rus/90_notes/storage_neurons_subworld.md`
- «смысл», алфавиты уровней и LLM-mode: `docs/rus/90_notes/meaning_alphabet_llm_mode.md`
- набросок системной архитектуры (термины): `docs/rus/90_notes/system_architecture_sketch.md`

Эти темы не должны требоваться для работы канонического L0 API (`detm/runtime/api.py`).
