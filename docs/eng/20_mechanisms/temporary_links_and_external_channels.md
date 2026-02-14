# Temporary links and external interaction channels

## Status

Canonical mechanism specification.

Note: first-pass translation of `docs/rus/20_mechanisms/temporary_links_and_external_channels.md`.

This card defines temporary links between grids/cells/levels in DETM.
Links represent external influence and cross-level transfer without synchronous barriers or acknowledgements.

---

## 1. Core idea

External interaction in DETM is modeled through time-bounded channels, not one-shot events.

A link is:
- temporary source-to-destination connection;
- active on a global-time interval;
- carrying its own transfer dynamics.

It models transfer process, not "accumulate and fire".

---

## 2. Link is not event and not ack

A link:
- is not an event "send dE now";
- does not require delivery acknowledgement;
- does not signal "processing completed".

Transfer itself is the interaction fact.

---

## 3. Formal link definition

```text
Link = {
  src,
  dst,
  start_tick,
  end_tick,
  rate,
  kernel,
  latency
}
```

Where:
- `src`/`dst` can be grids, regions, cells, or neighboring levels;
- `kernel` defines transfer shape (inertia/filter/leak);
- `latency` models delayed response.

---

## 4. Link as finite conductance

Link models limited conductance, not instant transfer.

Typical kernel:

```text
buffer[t+1] = buffer[t] + rate * (signal_src - buffer[t])
contribution = buffer[t]
```

RC-like behavior:
- smooths spikes;
- introduces inertia;
- prevents instantaneous jumps.

---

## 5. Links and global time

Links are active in global-time coordinates controlled by coarsener.

- `start_tick`/`end_tick` are expressed in base ticks;
- wall-clock seconds are interpreted into ticks externally;
- level change updates duration interpretation while preserving semantic meaning.

---

## 6. Cross-level links

Links can connect:
- entities on the same level;
- regions across neighboring levels.

Cross-level link is not refinement:
- refinement restores representability invariants;
- link is external interaction channel.

They are orthogonal mechanisms.

---

## 7. Link application in each step

Per global tick:
1. select active links (`start_tick <= t < end_tick`);
2. compute each contribution by its kernel;
3. sum contributions into external contour/input;
4. apply main lattice dynamics with this external input.

Links do not mutate state directly; they act through external contour coupling.

---

## 8. Links and asynchrony

Links enable asynchronous interaction:
- producer and consumer do not need strict lock-step synchronization;
- no completion barriers;
- no acknowledgement waits.

Coarsener only controls time and activation windows.

---

## 9. ComfyUI relation

In ComfyUI:
- nodes express intent to create/update/remove links;
- DETM runtime stores and applies active links;
- graph remains interface, not global-time engine.

---

## 10. Mechanism invariants

1. Link has finite lifetime.
2. Link acts via external contour/input.
3. Link does not require acknowledgements.
4. Link may be cross-level.
5. Link must not violate `E in [0,1]`.
6. Link does not replace refinement.

---

## 11. Purpose of this card

This card fixes canonical external-channel semantics in DETM.

