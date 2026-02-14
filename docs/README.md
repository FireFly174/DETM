# Documentation

This repository maintains documentation in two languages:

- Russian (canonical source): `docs/rus/`
- English (translation): `docs/eng/`

The folder structure under `rus/` and `eng/` is mostly mirrored.
Some section indices differ because RU docs evolved faster than EN translation
(for example, RU uses `40_hypotheses/50_experiments/60_limits`,
while EN keeps `30_hypotheses/40_experiments/50_limits`).

Start here:
- RU: `docs/rus/00_overview/README.md`
- EN: `docs/eng/00_overview/README.md`

Key docs:
- RU integration contract: `docs/rus/integration_contract.md`
- EN integration contract: `docs/eng/integration_contract.md`
- RU runtime/UI/viz architecture: `docs/rus/architecture.md`
- EN runtime/UI/viz architecture: `docs/eng/architecture.md`
- UML diagrams (PlantUML): `docs/uml/README.md`
- Legal/distribution docs: `docs/legal/README.md`

## Table of contents

- Overview
  - RU: `docs/rus/00_overview/README.md`
  - EN: `docs/eng/00_overview/README.md`
- Architecture (repo structure)
  - RU: `docs/rus/00_overview/architecture.md`
  - EN: `docs/eng/00_overview/architecture.md`
- Integration contract (L0 API)
  - RU: `docs/rus/integration_contract.md`
  - EN: `docs/eng/integration_contract.md`
- Runtime API (canonical execution layer)
  - RU: `docs/rus/30_architecture/runtime_api.md`
- Runtime/UI/viz architecture (current implementation)
  - RU: `docs/rus/architecture.md`
  - EN: `docs/eng/architecture.md`
- UML diagrams
  - `docs/uml/README.md`
- Model (core)
  - RU: `docs/rus/10_model/model_core.md`
  - EN: `docs/eng/10_model/model_core.md`
- DAGM core
  - RU: `docs/rus/10_model/dagm_core.md`
  - EN: `docs/eng/10_model/dagm_core.md`
- Mechanisms
  - Channels: RU `docs/rus/20_mechanisms/channels.md`, EN `docs/eng/20_mechanisms/channels.md`
  - Coarsening: RU `docs/rus/20_mechanisms/coarsening.md`, EN `docs/eng/20_mechanisms/coarsening.md`
  - Internal time: RU `docs/rus/20_mechanisms/internal_time.md`, EN `docs/eng/20_mechanisms/internal_time.md`
  - Invariants: RU `docs/rus/20_mechanisms/invariants.md`, EN `docs/eng/20_mechanisms/invariants.md`
  - Parameter fields: RU `docs/rus/20_mechanisms/parameter_fields.md`, EN `docs/eng/20_mechanisms/parameter_fields.md`
  - Level scale axis: RU `docs/rus/20_mechanisms/scale_axis.md`, EN `docs/eng/20_mechanisms/scale_axis.md`
  - Level scaling + refinement: RU `docs/rus/20_mechanisms/level_scaling_refinement.md`, EN `docs/eng/20_mechanisms/level_scaling_refinement.md`

- Hypotheses
  - RU: `docs/rus/40_hypotheses/hypotheses.md`
  - EN: `docs/eng/30_hypotheses/hypotheses.md`
  - Cards:
    - Attractors as objects: RU `docs/rus/40_hypotheses/attractors_as_objects.md`, EN `docs/eng/30_hypotheses/attractors_as_objects.md`
    - Boundary interface + holography: RU `docs/rus/40_hypotheses/boundary_interface_holography.md`, EN `docs/eng/30_hypotheses/boundary_interface_holography.md`
    - Inertia/mass from locality: RU `docs/rus/40_hypotheses/inertia_mass_locality.md`, EN `docs/eng/30_hypotheses/inertia_mass_locality.md`
    - Vortices as quasiparticles: RU `docs/rus/40_hypotheses/vortices_quasiparticles.md`, EN `docs/eng/30_hypotheses/vortices_quasiparticles.md`
    - Level capacity/phase transitions: RU `docs/rus/40_hypotheses/level_capacity_phase_transitions.md`, EN `docs/eng/30_hypotheses/level_capacity_phase_transitions.md`
    - e as scale/boundary step and O(1) normalization (RU only): `docs/rus/40_hypotheses/e_scale_boundary_invariants.md`
- Experiments
  - Golden baseline run (code/config): `experiments/00_baseline/README.md`
  - Research program (RU): `docs/rus/50_experiments/00_research_program.md`
  - Research program (EN): `docs/eng/40_experiments/00_research_program.md`
  - Baseline tests (RU): `docs/rus/50_experiments/01_baseline_tests.md`
  - Baseline tests (EN): `docs/eng/40_experiments/01_baseline_tests.md`
  - Regime transitions (RU): `docs/rus/50_experiments/02_regime_transition_tests.md`
  - Regime transitions (EN): `docs/eng/40_experiments/02_regime_transition_tests.md`
  - Metrics: RU `docs/rus/50_experiments/metrics.md`, EN `docs/eng/40_experiments/metrics.md`
  - Phase map: RU `docs/rus/50_experiments/exp_phase_map.md`, EN `docs/eng/40_experiments/exp_phase_map.md`
  - Object masks: RU `docs/rus/50_experiments/exp_object_masks.md`, EN `docs/eng/40_experiments/exp_object_masks.md`
  - Transfer speed: RU `docs/rus/50_experiments/exp_transfer_speed.md`, EN `docs/eng/40_experiments/exp_transfer_speed.md`
  - Channels: RU `docs/rus/50_experiments/exp_channels.md`, EN `docs/eng/40_experiments/exp_channels.md`
  - Density: RU `docs/rus/50_experiments/exp_density.md`, EN `docs/eng/40_experiments/exp_density.md`
  - Gradient: RU `docs/rus/50_experiments/exp_gradient.md`, EN `docs/eng/40_experiments/exp_gradient.md`
  - Marker scaling: RU `docs/rus/50_experiments/exp_marker_scaling.md`, EN `docs/eng/40_experiments/exp_marker_scaling.md`
  - Torus: RU `docs/rus/50_experiments/exp_torus.md`, EN `docs/eng/40_experiments/exp_torus.md`
  - Legacy data formats: RU `docs/rus/50_experiments/legacy_data_formats.md`, EN `docs/eng/40_experiments/legacy_data_formats.md`
- Limits
  - RU: `docs/rus/60_limits/limits.md`
  - EN: `docs/eng/50_limits/limits.md`
- Notes
  - Archive: RU `docs/rus/90_notes/archive.md`, EN `docs/eng/90_notes/archive.md`
  - Rewrite checklist: RU `docs/rus/90_notes/rewrite_checklist.md`, EN `docs/eng/90_notes/rewrite_checklist.md`
  - Source materials mapping: RU `docs/rus/90_notes/source_materials.md`, EN `docs/eng/90_notes/source_materials.md`
  - Single source of book concepts for DETM (RU only): `docs/rus/90_notes/book_concepts_single_source.md`
  - DETM learning model (RU only): `docs/rus/90_notes/learning_model_detm.md`
  - Readout/anti-Goodhart protocol (RU only): `docs/rus/90_notes/readout_protocol_and_antigoodhart.md`
  - Book / external framing (RU v2, non-canon): `docs/book/ru_v2/_compiled_v2.md`
  - Fallback/subworld: RU `docs/rus/90_notes/fallback_subworld.md`, EN `docs/eng/90_notes/fallback_subworld.md`
  - Storage formats: RU `docs/rus/90_notes/storage_neurons_subworld.md`, EN `docs/eng/90_notes/storage_neurons_subworld.md`
  - Meaning/alphabet/LLM-mode: RU `docs/rus/90_notes/meaning_alphabet_llm_mode.md`, EN `docs/eng/90_notes/meaning_alphabet_llm_mode.md`
- System architecture sketch: RU `docs/rus/90_notes/system_architecture_sketch.md`, EN `docs/eng/90_notes/system_architecture_sketch.md`



Вылито в "граните":
Если алгоритм не сообщает границы применимости,
то все его успехи — случайность,
а все провалы — вина пользователя.
