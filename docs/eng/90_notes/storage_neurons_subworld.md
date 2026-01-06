# Storage formats for level neurons and subworld (notes)

Note: first-pass translation of `docs/rus/90_notes/storage_neurons_subworld.md`.

Key principle:
- a level “neuron” is a compact O(1) invariant description (params + boundary response + signature)
- a subworld is a temporary compute object used for fallback and should not become a persistent “full grid artifact”

Useful overload metrics:
- `Fall(T)` as (fallback count × depth) intensity over a window
- `Instab(L;T)` as per-level fallback rate normalized by active neurons

Related notes:
- fallback/subworld: `docs/eng/90_notes/fallback_subworld.md`

