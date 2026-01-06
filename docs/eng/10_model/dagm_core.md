# DAGM core (Discrete Asynchronous Graph Model)

Note: this is a first-pass translation of `docs/rus/10_model/dagm_core.md`. If something is unclear, use the RU text as the source of truth.

---

## Purpose

DAGM is an abstract formulation of the same idea as DETM, but expressed on a graph:
- nodes and edges instead of lattice cells and neighborhood links
- explicit capacities/delays for local interactions
- asynchronous update as a first-class concept

The lattice model (DETM) is treated as a special case of DAGM.

---

## Model sketch

At a minimum, each node carries:
- a scalar “energy” value
- a structural/entropy-like suppression measure
- an internal time/latency state

Edges define local neighborhood and constrain flows.

Updates are deterministic and local; global behavior emerges from repeated application.

---

## Relation to coarsening

Coarsening can be discussed as:
- replacing a subgraph by an “effective” node/edge bundle
- preserving observables/invariants across scale changes
- defining multiple clocks/frequencies for different levels (streams)

---

## Practical note

In this repository:
- DAGM is documentation/spec tooling
- DETM is the executable L0 implementation

See also:
- `docs/eng/10_model/model_core.md`
- `docs/eng/20_mechanisms/coarsening.md`

