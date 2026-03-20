# Cross-Repo Reference Notes

Purpose: preserve useful patterns from adjacent repositories without importing them blindly into DETM.

This file is not canonical architecture. It is a transfer filter.

## Borrowable Pattern From `eplan-mcp/.codex`

What is worth borrowing:

- explicit split between repository context, tools, skills, and memory
- operational docs that help the agent start correctly without touching canon
- keeping repo-specific agent instructions in a dedicated namespace instead of scattering prompt files in the root

What should not be copied blindly:

- any assumption that the operational prompt stack is itself the source of model truth
- any workflow that encourages external worktrees by default
- any repo bootstrap flow that rewrites existing local agent infrastructure

## Transfer Rule For DETM

When porting an agent-workflow pattern from another repo, ask:

1. Does it help the agent recover context faster?
2. Does it keep canon in `docs/rus/*` rather than moving canon into prompt docs?
3. Does it preserve existing local layers such as `_mcp_launchers`, `.aimemo`, and ignored `AGENTS.md`?
4. Does it reduce root clutter without hiding important project truth?

Only if all answers are yes should the pattern be adopted.
