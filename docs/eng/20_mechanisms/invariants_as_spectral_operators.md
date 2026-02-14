# Invariants as spectral operators

## Status

Canonical mechanism specification.

Note: first-pass translation of `docs/rus/20_mechanisms/invariants_as_spectral_operators.md`.

This card defines DETM invariants as spectral response operators with their own internal time and resolution scale.

Invariants are not:
- stored trajectories;
- trained fixed weights;
- static saved states.

They are compact dynamic operators sufficient to reproduce level behavior.

---

## 1. Invariant is not state history

Invariant does not explicitly store:
- full interaction history;
- explicit time sequence.

Invariant stores:
- compressed state as integral of prior influence;
- internal reaction time scale;
- response operator under external impact.

History is compressed into state. Time is encoded in spectrum.

---

## 2. Invariant as response wave function

At level `Ln`, invariant can be represented as:

```text
Psi_Ln = Psi(E_in, direction, coupling, Tg_scale)
```

Where:
- `E_in`: incoming energy/influence;
- `direction`: transfer direction;
- `coupling`: interaction parameters;
- `Tg_scale`: global-time scale.

`Psi` encodes:
- accepted amount;
- forwarded amount;
- response pattern;
- temporal structure of response.

---

## 3. Internal (spectral) time

Each invariant has internal time `Ti`:

> minimal number of global ticks required for stable manifestation.

Consequences:
- fast invariants -> small `Ti`;
- slow/high-level invariants -> large `Ti`;
- levels group invariants by comparable `Ti`.

---

## 4. Levels as spectral windows

Level `Ln` corresponds to a range of internal times:
- `Ti ~= Tg(Ln)` -> stable representation;
- `Ti << Tg(Ln)` -> reduced/averaged out;
- `Ti >> Tg(Ln)` -> unresolved.

Level is a spectral window, not only spatial scale.

---

## 5. How invariants are stored

Store reproducibility parameters, not full trajectories:
- seed;
- environment parameters;
- response operator parameters;
- spectral characteristics.

Invariant storage is an operator library.

---

## 6. When invariant "does not know"

If invariant cannot respond coherently to input, this means:

> current spectral resolution is insufficient for the signal.

This is:
- not model failure;
- not undefined behavior;
- a resolution mismatch signal.

---

## 7. Refinement as spectral restoration

On spectral insufficiency:
- current invariant response is suspended;
- lower-level dynamics is activated;
- dynamics unfolds at higher effective frequency;
- result is aggregated back after resolution restoration.

Refinement is a normal spectral recovery operation.

---

## 8. Unity of influence and response

In DETM:
- influence and response are one operator chain;
- output of current step becomes input of next step;
- closure yields stability, not forbidden causal loops.

---

## 9. Full-scale composability

DETM is scale-composable because:
- any level can be represented via lower-level invariants;
- any invariant can be unfolded when resolution is insufficient;
- dynamic correctness is retained across this process.

This enables:
- keeping only active levels in memory;
- keeping others as operators;
- scaling without semantic loss.

---

## 10. Mechanism invariants

1. Invariant is a response operator.
2. Internal time sets reaction scale.
3. History is not stored explicitly.
4. Refinement restores spectral representability.
5. Levels correspond to spectral windows.

---

## 11. Purpose of this card

This card fixes canonical invariant interpretation in DETM.

