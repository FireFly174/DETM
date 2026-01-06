# Meaning, level alphabets, and LLM-mode (notes)

Note: first-pass translation of `docs/rus/90_notes/meaning_alphabet_llm_mode.md`.

Concepts:
- meaning as cross-level persistence under coarsening
- per-level alphabet `Σ_L` limiting expressivity
- overload as a trigger for fallback/subworld or alphabet growth
- LLM-mode: token → normalized field injection → dynamics → readout of invariant signatures

Minimal data check:
- take a state/trajectory at level `L` and apply coarsening (e.g. `2×2 → 1`, then `4×4 → 1`);
- compare stable proxies:
  - `corr(E_original, E_coarsed)` (or other robust summaries);
  - preservation of object counts/shapes via masks;
  - preservation of dominant frequencies/periods (if present).

Related notes:
- fallback/subworld: `docs/eng/90_notes/fallback_subworld.md`
- overload metrics: `docs/eng/90_notes/storage_neurons_subworld.md`
