#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

LINK_RE = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.*)$")

LAYER_BY_ROOT = {
    "rus": "canonical_ru",
    "eng": "translation",
    "book": "non_canon_book",
    "source": "source_archive",
    "media": "media",
    "uml": "uml",
    "legal": "legal",
}

STATUS_BY_LAYER = {
    "canonical_ru": "source_of_truth",
    "foundation": "source_of_truth",
    "translation": "derivative",
    "non_canon_book": "derivative",
    "source_archive": "archive",
    "media": "auxiliary",
    "uml": "auxiliary",
    "legal": "source_of_truth",
}

PURPOSE_BY_EXT = {
    ".puml": "UML source diagram",
    ".png": "Static image artifact",
    ".gif": "Animated visual artifact",
    ".mp4": "Video artifact",
    ".svg": "Vector diagram asset",
    ".pdf": "Exported PDF artifact",
    ".html": "Rendered HTML artifact",
    ".txt": "Tooling/log text artifact",
    ".log": "Execution log artifact",
    ".json": "Structured metadata artifact",
    ".canvas": "Raw canvas/source note artifact",
    "": "Auxiliary artifact",
}


def classify_layer(path: Path, docs_root: Path) -> str:
    rel = path.relative_to(docs_root)
    root = rel.parts[0] if rel.parts else ""
    return LAYER_BY_ROOT.get(root, "foundation")


def derive_purpose_from_md(text: str, default: str) -> str:
    for line in text.splitlines():
        m = HEADING_RE.match(line)
        if not m:
            continue
        title = re.sub(r"\s+#+\s*$", "", m.group(2).strip())
        if title:
            return title
    return default


def collect_key_points(text: str, max_points: int = 3) -> list[str]:
    points: list[str] = []
    for line in text.splitlines():
        m = HEADING_RE.match(line)
        if not m:
            continue
        title = re.sub(r"\s+#+\s*$", "", m.group(2).strip())
        if title:
            points.append(title)
        if len(points) >= max_points:
            break
    return points


def collect_links(text: str, max_links: int = 8) -> list[str]:
    links: list[str] = []
    for m in LINK_RE.finditer(text):
        dest = m.group(1).strip().split()[0]
        if not dest:
            continue
        if dest.startswith("http://") or dest.startswith("https://") or dest.startswith("mailto:"):
            continue
        links.append(dest)
        if len(links) >= max_links:
            break
    return links


def md_card(path: Path, docs_root: Path) -> dict[str, Any]:
    rel = path.relative_to(docs_root).as_posix()
    text = path.read_text(encoding="utf-8", errors="ignore")
    layer = classify_layer(path, docs_root)
    default_purpose = path.stem.replace("_", " ")
    purpose = derive_purpose_from_md(text, default_purpose)
    key_points = collect_key_points(text)
    links_to = collect_links(text)
    return {
        "path": f"docs/{rel}",
        "layer": layer,
        "purpose": purpose,
        "status": STATUS_BY_LAYER[layer],
        "key_points": key_points,
        "links_to": links_to,
    }


def non_md_item(path: Path, docs_root: Path) -> dict[str, Any]:
    rel = path.relative_to(docs_root).as_posix()
    layer = classify_layer(path, docs_root)
    ext = path.suffix.lower()
    purpose = PURPOSE_BY_EXT.get(ext, "Auxiliary non-markdown artifact")
    return {
        "path": f"docs/{rel}",
        "layer": layer,
        "purpose": purpose,
        "status": STATUS_BY_LAYER[layer],
        "extension": ext or "<noext>",
    }


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def build_summary_markdown(
    output_path: Path,
    run_id: str,
    pointer_entity: str,
    md_cards_path: Path,
    non_md_path: Path,
    cards: list[dict[str, Any]],
    inventory: list[dict[str, Any]],
) -> None:
    layer_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for c in cards:
        layer_counts[c["layer"]]["md"] += 1
    for item in inventory:
        layer_counts[item["layer"]]["non_md"] += 1

    total_md = len(cards)
    total_non_md = len(inventory)
    total_files = total_md + total_non_md

    lines: list[str] = []
    lines.append(f"# DETM Docs Memory Index Run - {run_id}")
    lines.append("")
    lines.append("## Run Metadata")
    lines.append("")
    lines.append(f"- Run entity: `DETM_docs_run_{run_id}`")
    lines.append(f"- Pointer entity: `{pointer_entity}`")
    lines.append("- Context: `detm-docs`")
    lines.append("- Provenance: `Source=docs/** via direct repository scan; aimemo markdown excluded`")
    lines.append("")
    lines.append("## Coverage")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Total files | {total_files} |")
    lines.append(f"| Markdown files | {total_md} |")
    lines.append(f"| Non-markdown files | {total_non_md} |")
    lines.append("")
    lines.append("## Layer Breakdown")
    lines.append("")
    lines.append("| Layer | `.md` | non-`.md` | Total |")
    lines.append("|---|---:|---:|---:|")
    for layer in sorted(layer_counts.keys()):
        md = layer_counts[layer]["md"]
        non = layer_counts[layer]["non_md"]
        lines.append(f"| `{layer}` | {md} | {non} | {md + non} |")
    lines.append("")
    lines.append("## Card Artifacts")
    lines.append("")
    lines.append(f"- Markdown cards (JSONL): `{md_cards_path.as_posix()}`")
    lines.append(f"- Non-markdown inventory (JSONL): `{non_md_path.as_posix()}`")
    lines.append("- Card schema: `path, layer, purpose, status, key_points, links_to`")
    lines.append("- Inventory schema: `path, layer, purpose, status, extension`")
    lines.append("")
    lines.append("## Retrieval Hints")
    lines.append("")
    lines.append("- `memory_search(context=\"detm-docs\", query=\"DETM_docs_run_\")`")
    lines.append("- `memory_search(context=\"detm-docs\", query=\"DETM_docs_canonical_ru_\")`")
    lines.append("- `memory_search(context=\"detm-docs\", query=\"DETM_docs_audit_\")`")
    lines.append("")
    lines.append("## Layer Contract")
    lines.append("")
    lines.append("- `foundation` and `canonical_ru` and `legal` -> `source_of_truth`")
    lines.append("- `translation` and `non_canon_book` -> `derivative`")
    lines.append("- `source_archive` -> `archive`")
    lines.append("- `media` and `uml` -> `auxiliary`")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build DETM docs memory index artifacts")
    parser.add_argument("--docs-root", default="docs", help="Path to docs root")
    parser.add_argument("--date", default=dt.date.today().isoformat(), help="Run date YYYY-MM-DD")
    parser.add_argument(
        "--out-md",
        default=None,
        help="Output markdown summary path (defaults to docs/rus/90_notes/docs_memory_index_run_<date>.md)",
    )
    parser.add_argument(
        "--out-cards",
        default=None,
        help="Output JSONL with markdown cards (defaults to docs/rus/90_notes/docs_memory_cards_<date>.jsonl)",
    )
    parser.add_argument(
        "--out-non-md",
        default=None,
        help="Output JSONL with non-markdown inventory (defaults to docs/rus/90_notes/docs_non_md_inventory_<date>.jsonl)",
    )
    parser.add_argument(
        "--pointer-entity",
        default="DETM_docs_index_pointer",
        help="Pointer entity name",
    )
    args = parser.parse_args()

    docs_root = Path(args.docs_root).resolve()
    if not docs_root.exists():
        raise SystemExit(f"docs root not found: {docs_root}")

    date_tag = args.date
    out_md = Path(args.out_md) if args.out_md else Path(f"docs/rus/90_notes/docs_memory_index_run_{date_tag}.md")
    out_cards = Path(args.out_cards) if args.out_cards else Path(f"docs/rus/90_notes/docs_memory_cards_{date_tag}.jsonl")
    out_non_md = Path(args.out_non_md) if args.out_non_md else Path(f"docs/rus/90_notes/docs_non_md_inventory_{date_tag}.jsonl")

    md_paths = sorted([p for p in docs_root.rglob("*.md") if p.is_file()])
    all_files = sorted([p for p in docs_root.rglob("*") if p.is_file()])
    non_md_paths = [p for p in all_files if p.suffix.lower() != ".md"]

    cards = [md_card(p, docs_root) for p in md_paths]
    inventory = [non_md_item(p, docs_root) for p in non_md_paths]

    write_jsonl(out_cards, cards)
    write_jsonl(out_non_md, inventory)

    run_id = date_tag.replace("-", "_")
    build_summary_markdown(
        output_path=out_md,
        run_id=run_id,
        pointer_entity=args.pointer_entity,
        md_cards_path=out_cards,
        non_md_path=out_non_md,
        cards=cards,
        inventory=inventory,
    )

    result = {
        "docs_root": docs_root.as_posix(),
        "total_files": len(all_files),
        "markdown_files": len(md_paths),
        "non_markdown_files": len(non_md_paths),
        "out_md": out_md.as_posix(),
        "out_cards": out_cards.as_posix(),
        "out_non_md": out_non_md.as_posix(),
        "run_entity": f"DETM_docs_run_{run_id}",
        "pointer_entity": args.pointer_entity,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
