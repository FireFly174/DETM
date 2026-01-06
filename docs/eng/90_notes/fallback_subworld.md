# Fallback / subworld / pipeline swap (notes)

Note: first-pass translation of `docs/rus/90_notes/fallback_subworld.md`.

This topic belongs to higher-level orchestration (ACGS) rather than L0 DETM and is kept as `90_notes`.

## Summary

Goal: keep computation close to O(1) in stable regimes by describing many cells as compact “neurons” (invariant operators), and only run detailed lower-level simulation on demand.

External analogies:
- “attention” in neural nets
- adaptive mesh refinement (AMR) in numerical physics
- locally adjustable “update rate” via `τ`

Two patterns:
- patch-fallback: cut out a local patch of `L-1`, simulate, then aggregate back
- pipeline swap (subworld): replace a single `L` neuron with a nested `L-1..L-k` simulation and communicate **only through boundary I/O**

Boundary-only constraint:
- no direct sharing of internal subworld state with neighbours
- no “energy summation up the levels”
- only condition/control via boundary interface

Practical trigger proxies (worth logging):
- large `|∇E|` (fronts/boundaries)
- large `|J|` (active transport)
- large `curl(J)` (cycles/vortices)
- increased local entropy/instability (via chosen suppression proxy)

Related notes:
- storage formats and resource criteria: `docs/eng/90_notes/storage_neurons_subworld.md`
- meaning/alphabet/LLM-mode: `docs/eng/90_notes/meaning_alphabet_llm_mode.md`
