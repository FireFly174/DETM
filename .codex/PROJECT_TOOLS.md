# Project Tools

Use repo-relevant tools first. DETM already has working local memory, repo git wiring, launcher commands, and filesystem tooling.

## Core Verification

- `pytest -q`
- `python main.py --help`
- targeted pytest paths for the area being changed

## Canonical Entry Points

- `python main.py`
- `python main.py napari --interactive`
- `python main.py headless ...`
- `python main.py shell ...`

## MCP Servers Worth Using Here

- `aimemo_detm_memory`
  - Primary repo memory for status recovery, decisions, and durable repo facts.
- `git_detm`
  - Repo-scoped git status, diff, log, add, and commit operations.
- `fast-filesystem`
  - Preferred file read/search helper when available and the allow-list is correct.
- `filesystem`
  - Safe fallback for file access.
- `server-win-cli`
  - Useful for Windows-specific shell checks and environment diagnostics.

## MCP Servers Available But Usually Secondary

- `playwright`
  - Useful only for browser-exposed flows or UI checks that genuinely need a browser.
- `comfyui-mcp`
  - Secondary and usually out of scope for core DETM runtime work.
- `lmstudio_qwen` and `lmstudio_retrieval`
  - Useful only for bounded delegation or ranking tasks.
- `sequentialthinking`
  - Useful when the task is ambiguous and needs structured reasoning.

## Repo-Local Supporting Layer

- `_mcp_launchers/*`
  - Reference layer for how external MCP tools are launched in this repo.
- `.aimemo/`
  - Repo-local aiMemo storage.
- local ignored `AGENTS.md`
  - Active local policy layer for this workspace.

## Practical Tool Order

1. Load repo memory.
2. Read `AGENTS.md` plus `.codex/*` operational docs.
3. Check canonical docs in `docs/rus/*`.
4. Inspect code and tests.
5. Verify with `pytest -q` and launcher smoke.

## Tool Guardrails

- Prefer repo memory over cross-project memory for DETM facts.
- Prefer repo git server over generic shell git when possible.
- Prefer main workspace edits over creating a worktree.
- Treat `_mcp_launchers/*` as existing infrastructure, not as auto-generated scratch files.
