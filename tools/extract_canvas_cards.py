from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class CanvasCard:
    source_canvas: Path
    canvas_id: str
    title: str
    tags: List[str]
    aliases: List[str]
    body: str


_FRONT_MATTER_RE = re.compile(r"\A\s*---\s*\r?\n(.*?)\r?\n---\s*(?:\r?\n|\Z)", re.DOTALL)


def _parse_inline_list(value: str) -> List[str]:
    value = value.strip()
    if not value.startswith("[") or not value.endswith("]"):
        return []
    inner = value[1:-1].strip()
    if not inner:
        return []
    items: List[str] = []
    for part in inner.split(","):
        item = part.strip().strip('"').strip("'")
        if item:
            items.append(item)
    return items


def _extract_front_matter(text: str) -> Tuple[List[str], List[str], str]:
    match = _FRONT_MATTER_RE.search(text)
    if not match:
        return [], [], text

    fm = match.group(1)
    tags: List[str] = []
    aliases: List[str] = []

    for raw in fm.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("tags:"):
            tags = _parse_inline_list(line.split(":", 1)[1])
        if line.startswith("aliases:"):
            aliases = _parse_inline_list(line.split(":", 1)[1])

    body = text[match.end() :]
    return tags, aliases, body


def _title_from_markdown(text: str) -> str:
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("#"):
            title = line.lstrip("#").strip()
            return title.strip("`").strip()
    first = text.strip().splitlines()[0] if text.strip() else "untitled"
    return first[:80].strip("`").strip()


def _load_canvas_nodes(path: Path) -> List[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return []
    nodes = data.get("nodes", [])
    if not isinstance(nodes, list):
        return []
    out: List[dict[str, Any]] = []
    for node in nodes:
        if isinstance(node, dict):
            out.append(node)
    return out


def iter_canvas_cards(canvas_path: Path) -> Iterator[CanvasCard]:
    for node in _load_canvas_nodes(canvas_path):
        if node.get("type") != "text":
            continue
        text = node.get("text")
        if not isinstance(text, str):
            continue

        tags, aliases, body = _extract_front_matter(text)
        title = _title_from_markdown(body if body.strip() else text)
        canvas_id = str(node.get("id") or "").strip() or "unknown"

        body_out = body.strip() if body.strip() else text.strip()
        if body_out and not body_out.startswith("#"):
            body_out = f"# {title}\n\n{body_out}"

        yield CanvasCard(
            source_canvas=canvas_path,
            canvas_id=canvas_id,
            title=title,
            tags=tags,
            aliases=aliases,
            body=body_out + "\n",
        )


def _safe_rel_dir(path: Path, base: Path) -> Path:
    rel = path.relative_to(base)
    parts = list(rel.parts)
    if parts and parts[-1].lower().endswith(".canvas"):
        parts[-1] = parts[-1][: -len(".canvas")]
    return Path(*parts)


def _write_card(path: Path, card: CanvasCard) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    def yaml_list(items: Sequence[str]) -> str:
        if not items:
            return "[]"
        escaped = [item.replace('"', '\\"') for item in items]
        return "[" + ", ".join(f'"{v}"' for v in escaped) + "]"

    escaped_title = card.title.replace("\\", "\\\\").replace('"', '\\"')
    try:
        repo_root = Path.cwd().resolve()
        source_canvas = card.source_canvas.resolve().relative_to(repo_root)
    except Exception:
        source_canvas = card.source_canvas
    fm_lines = [
        "---",
        f'title: "{escaped_title}"',
        f'source_canvas: "{source_canvas.as_posix()}"',
        f'canvas_id: "{card.canvas_id}"',
        f"tags: {yaml_list(card.tags)}",
        f"aliases: {yaml_list(card.aliases)}",
        "---",
        "",
    ]
    content = "\n".join(fm_lines) + card.body
    path.write_text(content, encoding="utf-8")


def _write_index(path: Path, entries: List[Tuple[Path, int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: List[str] = [
        "# Canvas cards",
        "",
        "This folder is generated from Obsidian `.canvas` files and contains one markdown file per text node.",
        "",
        "Regenerate:",
        "",
        "```bash",
        "python tools/extract_canvas_cards.py --source \"docs/source/Discrete Emergent Medium with Multilevel Coarsening\" --out \"docs/source/cards\"",
        "```",
        "",
        "## Sources",
        "",
    ]
    for rel_dir, count in sorted(entries, key=lambda x: x[0].as_posix()):
        lines.append(f"- `{rel_dir.as_posix()}`: {count} cards")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def extract_cards(source_dir: Path, out_dir: Path) -> None:
    source_dir = source_dir.resolve()
    out_dir = out_dir.resolve()

    entries: List[Tuple[Path, int]] = []
    for canvas_path in sorted(source_dir.rglob("*.canvas")):
        rel_dir = _safe_rel_dir(canvas_path, source_dir)
        card_out_dir = out_dir / rel_dir
        count = 0
        for card in iter_canvas_cards(canvas_path):
            out_path = card_out_dir / f"card_{card.canvas_id}.md"
            _write_card(out_path, card)
            count += 1
        entries.append((rel_dir, count))

    _write_index(out_dir / "README.md", entries)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Extract text nodes from Obsidian canvas into markdown cards.")
    ap.add_argument("--source", required=True, help="Directory containing .canvas files (recursively scanned).")
    ap.add_argument("--out", required=True, help="Output directory for generated cards.")
    args = ap.parse_args(argv)

    extract_cards(Path(args.source), Path(args.out))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
