# DETM Memory Playbook (aiMemo-first)

## Purpose

Operational runbook for docs ingestion, file-level code map sync, and cross-project bridge synchronization in DETM.

## Source-of-Truth Policy

- Allowed source inputs: `docs/**` only.
- Primary memory endpoint for DETM: `memdetm`.
- Global bridge endpoint for cross-project links: `memglobal`.
- Forbidden as source input: `aimemo/*.md` and any local generated summary markdown.
- Docs-ops generated outputs live in `docs/source/generated/docs_ops/` and must not be written back into `docs/rus/90_notes/`.

## Hybrid Graph Topology (canonical)

- DETM local store: `D:\github\DETM\.aimemo\memory.db`
- Global hub store: `C:\Users\FireFly74\.aimemo\memory.db`
- Cross-project relations are not written directly between stores.
- Cross-project relations are materialized as `XREF::*` bridge entities in global hub.

## Mandatory Normalized Tags

Each entity must include:

- `proj:detm` (or `proj:global` for bridge entities)
- `lvl:core_contract|execution_memory|artifact_schema|orchestration`
- `kind:docs|code|decision|module|system|project|run|bridge`
- `state:fact|hypothesis|assumption|mixed`

## Canon-first Layer Rules

- `foundation`, `canonical_ru`, `legal`: authoritative (`source_of_truth`).
- `translation`, `non_canon_book`: derivative.
- `source_archive`: archive.
- `media`, `uml`: auxiliary.

## Standard Run (manual refresh)

1. Generate docs inventory and cards:
```powershell
python tools/build_docs_memory_index.py --date <YYYY-MM-DD> --out-md docs/source/generated/docs_ops/docs_memory_index_run_<YYYY-MM-DD>.md --out-cards docs/source/generated/docs_ops/docs_memory_cards_<YYYY-MM-DD>.jsonl --out-non-md docs/source/generated/docs_ops/docs_non_md_inventory_<YYYY-MM-DD>.jsonl
```

2. Refresh runtime hotspot triage (detector only):
```powershell
python tools/runtime_hotspot_scan.py --repo-root . --roots detm detm_app --policy tools/oop_gatekeeper_policy.yaml --out-json docs/source/generated/docs_ops/runtime_oop_hotspots_<YYYY-MM-DD>.json --out-md docs/source/generated/docs_ops/runtime_oop_hotspots_<YYYY-MM-DD>.md
```

3. Run link checks for canonical subset:
```powershell
python tools/check_markdown_links.py docs/README.md docs/BRANCHING.md docs/integration_contract.md docs/rus/README.md docs/eng/README.md
```

4. Sync docs entities into `memdetm`:
```powershell
python D:\01 Projects\_aimemo-control\scripts\memory_sync_docs.py --project detm --mode delta --endpoint memdetm --cards-jsonl docs/source/generated/docs_ops/docs_memory_cards_<YYYY-MM-DD>.jsonl --inventory-jsonl docs/source/generated/docs_ops/docs_non_md_inventory_<YYYY-MM-DD>.jsonl
```

5. Sync file-level code map into `memdetm`:
```powershell
python D:\01 Projects\_aimemo-control\scripts\memory_sync_codemap.py --project detm --mode delta --endpoint memdetm --graph-db D:\01 Projects\agency-runtime\graph-sdk\data\graph.db
```

6. Refresh cross-project bridges in `memglobal`:
```powershell
python D:\01 Projects\_aimemo-control\scripts\memory_sync_xref.py --threshold 0.62
```

## Required Memory Entity Patterns

- Docs file entity: `DOC_FILE::detm::<repo_rel_path>`
- Code file entity: `CODE_FILE::detm::<repo_rel_path>`
- Docs run entity: `DOC_RUN::detm::<YYYYMMDD_HHMMSS>::<sha8>`
- Code run entity: `CODE_RUN::detm::<YYYYMMDD_HHMMSS>::<sha8>`
- Docs pointer: `MEM_PTR::detm::docs`
- Code pointer: `MEM_PTR::detm::code`
- Global explicit bridge: `XREF::<from_proj>::<to_proj>::<relation>::<evidence_hash8>`
- Global heuristic bridge candidate: `XREFCAND::<from_proj>::<to_proj>::<relation>::<evidence_hash8>`

## Observation Format Contract

Every observation should start with one of:

- `FACT:`
- `HYPOTHESIS:`
- `ASSUMPTION:`

Mandatory provenance line for run/layer/audit entities:

- `FACT: Source=docs/** via direct repository scan; local aimemo markdown is not a source-of-truth input.`

Mandatory locator lines for `DOC_FILE::*` and `CODE_FILE::*`:

- `FACT: locator.path=<repo_rel_path>`
- `FACT: locator.symbol=<qualname|__file__>`
- `FACT: locator.span=<start_line>:<end_line>`
- `FACT: locator.commit_sha=<git_sha_or_na>`
- `FACT: locator.content_sha256=<sha256>`
- `FACT: source_kind=<docs|code>`
- `FACT: source_project=detm`

## Required Graph Links

- run -> layer (`implements`)
- layer -> artifacts/files (`depends_on`)
- canonical RU -> EN translation (`related_to`)
- canonical -> archive/book (`related_to`)
- audit finding -> impacted layer (`fixes` or `related_to`)
- runtime hotspots -> OOP concept bridge (`related_to` -> `MCP_OOP_Gatekeeper_*`)
- cross-project relation -> global bridge entity:
  - `XREF::<from_proj>::<to_proj>::<relation>::<id>`
  - with observations `from_locator`, `to_locator`, `relation`, `source_relation_id`
  - heuristic candidates are written as `XREFCAND::<from_proj>::<to_proj>::<relation>::<evidence_hash8>`

## Retrievability Checks

```text
memdetm.memory_search(query="DOC_RUN::detm::", limit=20)
memdetm.memory_search(query="DOC_FILE::detm::", limit=50)
memdetm.memory_search(query="CODE_FILE::detm::", limit=50)
memglobal.memory_search(query="XREF::detm::", limit=20)
memglobal.memory_search(query="XREFCAND::detm::", limit=20)
```

Expected outcome:

- run + file-level entities are returned,
- cross-project links are discoverable via `XREF::*` in global hub,
- heuristic candidates are discoverable via `XREFCAND::*` in global hub,
- provenance excludes `aimemo/*.md` as source.

## Verification

```text
powershell -NoProfile -ExecutionPolicy Bypass -File D:\01 Projects\_aimemo-control\scripts\memory_verify_hybrid.ps1
```

Expected outcome:

- routing and isolation checks pass,
- tags include `proj:*`, `lvl:*`, `kind:*`, `state:*`,
- every `DOC_FILE::*` and `CODE_FILE::*` has full locator contract.
