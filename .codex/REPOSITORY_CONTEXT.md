# Repository Context

Repository: `DETM`

## Mission

Develop DETM as a research-grade runtime and observability stack for discrete lattice dynamics while preserving the architectural boundary between:

- `detm/*` as library-core and contracts
- `detm_app/*` as orchestration, UI, transport, and subscribers

The agent environment in this repo must help execution and status recovery without becoming a second source of truth for the model.

## Architecture In One Pass

- `detm/`
  - Core runtime, contracts, serialization, level policy, fabric, pattern memory.
- `detm_app/`
  - Session orchestration, subscribers, UI runtime, headless shell, napari path.
- `docs/rus/`
  - Canonical documentation and roadmap.
- `.codex/`
  - Operational agent context for Codex.
- `_mcp_launchers/`
  - Repo-local launcher/reference layer for MCP wiring and repair.

## Canonical Sources

For model and roadmap truth, prefer:

1. `docs/rus/ROADMAP.md`
2. `docs/rus/ROADMAP_HUMAN.md`
3. `docs/rus/90_notes/book_concepts_single_source.md`
4. `docs/rus/90_notes/learning_model_detm.md`
5. `docs/rus/90_notes/readout_protocol_and_antigoodhart.md`
6. `docs/rus/40_hypotheses/hypotheses.md`

`.codex/*` is operational context only. It must not redefine DETM canon.

## Current Engineering Direction

- Fabric baseline is done as baseline.
- Main open engineering work is still `WS-F`, then `WS-G-ND`, then residual runtime debt.
- `exploration_horizon_*` is now part of the F-track readout contour.
- External observability remains artifact-first: `System Trace`, `Watch Trace`, `trace_ref`, `watch_contract`.

## Constraints And Guardrails

- Do not treat prompt docs as stronger than roadmap and canonical notes.
- Do not widen orchestration or agent convenience into model canon.
- Do not optimize a single KPI and call that progress.
- Do not let repo-local agent setup overwrite `_mcp_launchers`, `.aimemo`, or local ignored `AGENTS.md` casually.
- Do not use off-repo worktrees by default for DETM. Work in the main workspace unless the user explicitly asks for isolation.

## Important Working Files

- `AGENTS.md` (local ignored repo policy layer)
- `.codex/PROMT.md`
- `.codex/SYSTEM_PROMT_DETM_CREATIVE.md`
- `.codex/PROJECT_TOOLS.md`
- `.codex/PROJECT_SKILLS.md`
- `.codex/PROJECT_MEMORY.md`
- `docs/rus/90_notes/agent_workspace_preservation.md`

## Worktree Policy

- Default: no worktree.
- If isolation is explicitly needed, prefer a repo-local path such as `.worktrees/` under the repository, not an external disk/location.
- After merge/push, stale worktrees should be removed.
