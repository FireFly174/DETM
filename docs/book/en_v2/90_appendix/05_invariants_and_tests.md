# Invariants and tests

This checklist aligns book-level diagnostics with repo-level verification.

## Invariants

1. Causality can be measured (no blind optimization).
2. Readout is multi-signal (anti-Goodhart).
3. Basis stress is visible before collapse.
4. Rule changes preserve rollback path.
5. Transition criteria are explicit before regime switch.

## Practical tests

- reproducible headless runs (`catalog/metrics/summary/final_state`),
- trace/watch linkage (`trace_ref` continuity),
- metric-countermetric consistency,
- no hidden dependency from core (`detm/*`) to app UI.

For current execution status, see `docs/rus/ROADMAP.md`.