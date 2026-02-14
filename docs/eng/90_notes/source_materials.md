# Source materials coverage

Note: first-pass translation of `docs/rus/90_notes/source_materials.md`.

Originally, most ideas and formulations lived as working notes (Markdown + Obsidian `.canvas`).
Those sources are treated as **local raw material** and are **not tracked by git** (you can keep them next to the repo or in a local `docs/source/` folder, which is ignored).

This page records where the canonical docs live and which themes have been transferred into `docs/rus/` (and mirrored into `docs/eng/`).

---

## 1) Principles

- `docs/rus/` is canonical (code and experiments rely on it).
- `docs/eng/` is a translation (may be incomplete/simplified).
- raw notes / `.canvas` exports are not part of the canon.

If you want to locally extract `.canvas` text nodes into markdown “cards”, use `tools/extract_canvas_cards.py` (outputs are local-only and should not be committed).

---

## 2) Canon coverage (where things live)

- DAGM (graph formulation): `docs/rus/10_model/dagm_core.md`
- DETM (lattice spec): `docs/rus/10_model/model_core.md`
- Mechanisms: `docs/rus/20_mechanisms/*`
  - internal time/asynchrony: `docs/rus/20_mechanisms/internal_time.md`
  - environment parameters as fields: `docs/rus/20_mechanisms/parameter_fields.md`
  - coarsening/scale: `docs/rus/20_mechanisms/coarsening.md`, `docs/rus/20_mechanisms/scale_axis.md`
- Hypotheses (list): `docs/rus/30_hypotheses/hypotheses.md`
- Experiments and metrics: `docs/rus/40_experiments/*`
  - metrics: `docs/rus/40_experiments/metrics.md`
  - regime phase maps: `docs/rus/40_experiments/exp_phase_map.md`
  - object masks/boundaries: `docs/rus/40_experiments/exp_object_masks.md`
  - transfer speed/lags: `docs/rus/40_experiments/exp_transfer_speed.md`
- Limits: `docs/rus/50_limits/limits.md`

---

## 3) “Canvas card” extractions (integrated)

Themes extracted from `.canvas` were integrated into dedicated pages:

- attractors as “objects”: `docs/eng/30_hypotheses/attractors_as_objects.md`
- boundary as interface + “holography”: `docs/eng/30_hypotheses/boundary_interface_holography.md`
- inertia/“mass” from locality: `docs/eng/30_hypotheses/inertia_mass_locality.md`
- vortices as quasiparticles: `docs/eng/30_hypotheses/vortices_quasiparticles.md`
- level capacity and phase transitions: `docs/eng/30_hypotheses/level_capacity_phase_transitions.md`

---

## 4) Out-of-scope for L0 canon (but worth keeping)

Higher-level topics (L>0 and/or orchestration) are stored as `90_notes`:

- fallback/subworld: `docs/eng/90_notes/fallback_subworld.md`
- storage formats and resource criteria: `docs/eng/90_notes/storage_neurons_subworld.md`
- meaning/alphabet/LLM-mode: `docs/eng/90_notes/meaning_alphabet_llm_mode.md`
- system architecture sketch: `docs/eng/90_notes/system_architecture_sketch.md`

These notes must not be required by the canonical L0 API (`detm/runtime/api/*`).
