# Project Memory

This repository uses repo-local aiMemo memory backed by `D:\github\DETM\.aimemo\memory.db`.

## Memory Servers

- Primary repo memory: `aimemo_detm_memory`
- Optional cross-project recall: `aimemo_global_memory`
- Agent-only memory: `aimemo_agent_memory`

## What Belongs In Repo Memory

- roadmap status and current engineering phase
- architecture decisions and explicit transition constraints
- verified behavior of runtime, watch/readout, fabric, and tooling
- repo-local workflow facts such as preferred verification and environment constraints

## What Does Not Belong There

- personal style preferences with no repo impact
- unrelated project facts
- speculative claims not checked against code, docs, or tests

## Stable Repo Facts

- `detm/*` is core; `detm_app/*` is orchestration/UI/transport.
- External observability is artifact-first.
- F-track is still an open engineering contour.
- `.codex/*` is operational context, not model canon.
- Local ignored `AGENTS.md` is part of the active workspace setup.

## Session Startup Checklist

1. Load `aimemo_detm_memory`.
2. Read local `AGENTS.md`.
3. Read `.codex/REPOSITORY_CONTEXT.md`, `.codex/PROJECT_TOOLS.md`, `.codex/PROJECT_SKILLS.md`.
4. If bootstrap is requested, read `.codex/SYSTEM_PROMT_DETM_CREATIVE.md` and `.codex/PROMT.md`.
5. Then open canonical docs from `docs/rus/*`.
