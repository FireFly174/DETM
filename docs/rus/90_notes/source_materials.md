# Исходные материалы и покрытие документацией

Изначально большая часть идей и формулировок велась как «поток заметок» (Markdown + Obsidian `.canvas`).
Эти исходники рассматриваются как **локальное сырьё** и **не трекаются git** (их можно хранить рядом с репозиторием или в локальной папке `docs/source/`, которая игнорируется).

Цель этого файла — зафиксировать, где находится канон, и какие темы из исходников уже перенесены в структуру `docs/rus/` (и переведены в `docs/eng/`).

---

## 1) Принцип

- `docs/rus/` — каноническая документация (на неё опираются код и эксперименты).
- `docs/eng/` — перевод (может быть неполным/упрощённым).
- `docs/book/ru/` — «книга» / внешняя рамка (не канон, публицистика/обобщение идей поверх проекта).
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
  - пропускная способность границы и масштабирование по периоду: `docs/rus/20_mechanisms/boundary_throughput_and_period_scaling.md`
- Гипотезы (список): `docs/rus/40_hypotheses/hypotheses.md`
- Эксперименты и метрики: `docs/rus/50_experiments/*`
  - метрики: `docs/rus/50_experiments/metrics.md`
  - фазовые карты режимов: `docs/rus/50_experiments/exp_phase_map.md`
  - маски/границы объектов: `docs/rus/50_experiments/exp_object_masks.md`
  - скорость переноса/лаги: `docs/rus/50_experiments/exp_transfer_speed.md`
- Ограничения (limits): `docs/rus/60_limits/limits.md`

---

## 3) Карточки‑расширения (выжимка из canvas)

Следующие темы из исходных `.canvas` перенесены как отдельные карточки/протоколы:

- аттракторы как «объекты»: `docs/rus/40_hypotheses/attractors_as_objects.md`
- граница как интерфейс и «голографичность»: `docs/rus/40_hypotheses/boundary_interface_holography.md`
- инерция/«масса» из локальности: `docs/rus/40_hypotheses/inertia_mass_locality.md`
- вихри как квазичастицы: `docs/rus/40_hypotheses/vortices_quasiparticles.md`
- ёмкость уровня и фазовые переходы: `docs/rus/40_hypotheses/level_capacity_phase_transitions.md`
- e как естественный шаг масштаба/границы и O(1)-нормировка: `docs/rus/40_hypotheses/e_scale_boundary_invariants.md`

---

## 4) Что явно вне канона L0 (но важно не потерять)

Темы про уровни выше L0 и/или оркестрацию (ACGS) хранятся в `90_notes`:

- fallback/subworld: `docs/rus/90_notes/fallback_subworld.md`
- форматы хранения нейронов/subworld и ресурсные критерии: `docs/rus/90_notes/storage_neurons_subworld.md`
- «смысл», алфавиты уровней и LLM-mode: `docs/rus/90_notes/meaning_alphabet_llm_mode.md`
- манифест про «ИИ с L0» и `τ`: `docs/rus/90_notes/ai_with_L0_manifesto.md`
- поперечное поле консенсуса `C` / `L⊥`: `docs/rus/90_notes/consensus_field_across_levels.md`
- «два раза — и меняем измерение» (memory layers): `docs/rus/90_notes/two_strikes_change_dimension.md`
- «архитектурно нечестное» (эксплойт интерпретатора/метрик): `docs/rus/90_notes/architecturally_unfair_interactions.md`
- межкомпанийнный пул задач и синхронизация уровней: `docs/rus/90_notes/intercompany_level_sync_task_pool.md`
- anti‑capture: защита системы от захвата и вырождения: `docs/rus/90_notes/anti_capture_and_degeneracy.md`
- инженерный паспорт решения (шаблон): `docs/rus/90_notes/solution_passport.md`
- инженерный паспорт DETM (заполненный черновик): `docs/rus/90_notes/DETM_solution_passport_filled.md`
- вариационная/гамильтонова интерпретация DETM: `docs/rus/90_notes/variational_interpretation.md`
- набросок системной архитектуры (термины): `docs/rus/90_notes/system_architecture_sketch.md`
- статус-снимок и план извлечения из книги (2026-02-09): `docs/rus/90_notes/status_recovery_2026-02-09.md`
- спецификация кодовой базы (snapshot 2026-02-09): `docs/rus/90_notes/codebase_spec_2026-02-09.md`
- единый источник концепций книги для DETM: `docs/rus/90_notes/book_concepts_single_source.md`
- модель обучения DETM (удержание инварианта): `docs/rus/90_notes/learning_model_detm.md`
- протокол readout/anti-Goodhart: `docs/rus/90_notes/readout_protocol_and_antigoodhart.md`
- архив двух архитектурных вариантов (L0-подписчики vs Node/Fabric): `docs/rus/90_notes/architecture_variants_l0_and_fabric_2026-02-09.md`

Эти темы не должны требоваться для работы канонического L0 API (`detm/runtime/api/*`).

