# Project Skills

Use global Codex skills only when they improve execution for DETM. The local repo contract and canonical docs remain primary.

## Core Skills

- `systematic-debugging`
  - Use before fixing unexpected runtime behavior, failing tests, or broken tooling.
- `verification-before-completion`
  - Use before claiming work is done.
- `requesting-code-review`
  - Useful after a meaningful feature batch.
- `receiving-code-review`
  - Useful when review feedback needs technical verification.
- `code-review`
  - Useful when the task is explicitly a review and findings are the main output.

## Planning And Execution

- `writing-plans`
  - Use before multi-step work when a plan is actually needed.
- `executing-plans`
  - Use when there is already a written implementation plan.
- `wrap-session`
  - Useful for handoff/session close.
- `code-documentation`
  - Useful for docs and runbook updates.

## Skills To Treat Carefully In DETM

- `bootstrap-repository`
  - Do not use here for routine repo adaptation. DETM already has hand-built local agent infrastructure and this can overwrite important pieces.
- `using-git-worktrees`
  - Do not use by default in DETM. Use only if the user explicitly asks for worktree isolation or there is a clearly justified repo-local worktree path.

## Potentially Useful Secondary Skills

- `skill-search`
  - Useful when the right skill is unclear.
- `local-lmstudio-agents`
  - Useful only for bounded side tasks.
- `code-refactoring`
  - Useful for structural cleanup without behavior change.
- `recover-technical-intent`
  - Use when the question is incomplete, noisy, or structurally broken. This is an analysis skill to figure out what the question is really asking and what to do next.
  
## Usually Not Worth Using Here

- business, GTM, growth, outreach, and other non-engineering skills
- generic design-heavy frontend skills unless the task is specifically about the napari/UI layer

## Repo Rules

- Skills are execution aids, not sources of architectural truth.
- No skill should override DETM canon from roadmap and core notes.
- No skill should rewrite local ignored environment files unless that rewrite is deliberate and reviewable.
