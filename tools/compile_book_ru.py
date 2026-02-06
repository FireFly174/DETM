#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import pathlib
import re
import sys
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple


@dataclass(frozen=True)
class Chapter:
    path: pathlib.Path
    title: str
    body_lines: List[str]


PAD_RE = re.compile(r"^\s*<!--\s*PAD:\s*\.{5,}\s*-->\s*$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
ADMONITION_START_RE = re.compile(r"^>\s*\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*$")


def load_manifest(manifest_path: pathlib.Path) -> List[pathlib.Path]:
    root = manifest_path.parent
    files: List[pathlib.Path] = []
    for raw in manifest_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        files.append((root / line).resolve())
    return files


def strip_pad(lines: Sequence[str]) -> List[str]:
    return [l for l in lines if not PAD_RE.match(l)]


def strip_draft_blocks(lines: Sequence[str]) -> List[str]:
    out: List[str] = []
    in_block = False
    for line in lines:
        if line.strip() == "<!-- @draft-begin -->":
            in_block = True
            continue
        if line.strip() == "<!-- @draft-end -->":
            in_block = False
            continue
        if not in_block:
            out.append(line)
    return out


def strip_draft_markers_only(lines: Sequence[str]) -> List[str]:
    markers = {"<!-- @draft-begin -->", "<!-- @draft-end -->"}
    return [l for l in lines if l.strip() not in markers]


def strip_admonitions(lines: Sequence[str]) -> List[str]:
    out: List[str] = []
    i = 0
    n = len(lines)
    while i < n:
        if ADMONITION_START_RE.match(lines[i]):
            i += 1
            # Consume following quote lines ("> ...") and optional blank quote lines.
            while i < n and (lines[i].startswith(">") or lines[i].strip() == ""):
                # Stop at first non-quote, non-empty line.
                if lines[i].strip() != "" and not lines[i].startswith(">"):
                    break
                i += 1
            # Skip trailing single blank line after admonition if present.
            if i < n and lines[i].strip() == "":
                i += 1
            continue
        out.append(lines[i])
        i += 1
    return out


def shift_headings(lines: Sequence[str], delta: int) -> List[str]:
    if delta <= 0:
        return list(lines)
    out: List[str] = []
    in_fence = False
    fence_marker = ""
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            marker = stripped[:3]
            if not in_fence:
                in_fence = True
                fence_marker = marker
            elif fence_marker == marker:
                in_fence = False
                fence_marker = ""
            out.append(line)
            continue
        if in_fence:
            out.append(line)
            continue
        m = HEADING_RE.match(line)
        if not m:
            out.append(line)
            continue
        hashes, rest = m.group(1), m.group(2)
        new_level = min(6, len(hashes) + delta)
        out.append("#" * new_level + " " + rest)
    return out


def extract_title(lines: Sequence[str], fallback: str) -> Tuple[str, int | None]:
    in_fence = False
    fence_marker = ""
    for idx, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            marker = stripped[:3]
            if not in_fence:
                in_fence = True
                fence_marker = marker
            elif fence_marker == marker:
                in_fence = False
                fence_marker = ""
            continue
        if in_fence:
            continue
        m = HEADING_RE.match(line)
        if m and len(m.group(1)) == 1:
            return m.group(2).strip(), idx
    return fallback, None


def normalize_chapter(
    path: pathlib.Path,
    mode: str,
    heading_delta: int,
) -> Chapter:
    raw_lines = path.read_text(encoding="utf-8").splitlines()
    lines = strip_pad(raw_lines)

    if mode == "print":
        lines = strip_draft_blocks(lines)
        lines = strip_admonitions(lines)
    else:
        # Keep draft note content, but remove marker lines for readability.
        lines = strip_draft_markers_only(lines)

    title, title_idx = extract_title(lines, fallback=path.stem)
    if mode == "print":
        title = re.sub(r"\s*\([^)]*черновик[^)]*\)\s*$", "", title, flags=re.IGNORECASE).strip()

    # Remove the top-level title line; we will generate a unified ToC + keep titles as H2/H3...
    if title_idx is not None:
        lines = lines[:title_idx] + lines[title_idx + 1 :]

    # Remove leading blank lines for nicer concatenation.
    while lines and lines[0].strip() == "":
        lines.pop(0)

    lines = shift_headings(lines, heading_delta)
    return Chapter(path=path, title=title, body_lines=lines)


def estimate_pages(text: str) -> float:
    # Very rough: ~1800 chars (with spaces) per page.
    return len(text) / 1800.0


def count_words(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text, flags=re.UNICODE))


def chapter_stats(ch: Chapter) -> Tuple[int, int]:
    body = "\n".join(ch.body_lines)
    return count_words(body), len(body)


def print_report(chapters: Sequence[Chapter], mode: str) -> None:
    print(f"Report: chapters={len(chapters)} mode={mode}", file=sys.stderr)
    total_words = 0
    total_chars = 0
    for idx, ch in enumerate(chapters, 1):
        words, chars = chapter_stats(ch)
        total_words += words
        total_chars += chars
        print(
            f"{idx:02d}. words={words:6d} chars={chars:7d} file={ch.path.name}",
            file=sys.stderr,
        )
    print(f"Total: words={total_words} chars={total_chars}", file=sys.stderr)


def build_book(
    chapter_paths: Sequence[pathlib.Path],
    mode: str,
    include_glossary: bool,
) -> Tuple[List[Chapter], List[str]]:
    missing = [p for p in chapter_paths if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing files:\n" + "\n".join(str(p) for p in missing))

    chapters: List[Chapter] = []
    warnings: List[str] = []

    for p in chapter_paths:
        if not include_glossary and p.name == "01_terms.md":
            continue
        chapters.append(normalize_chapter(p, mode=mode, heading_delta=1))

    # Basic sanity warnings.
    for ch in chapters:
        if mode == "print" and "черновик" in ch.title.lower():
            warnings.append(f'Title contains "черновик": {ch.path.name}')
        if any("TODO" in l for l in ch.body_lines):
            warnings.append(f"Contains TODO: {ch.path.name}")

    return chapters, warnings


def render(
    chapters: Sequence[Chapter],
    title: str,
    mode: str,
    include_toc: bool,
    include_stats: bool,
) -> str:
    out: List[str] = []
    out.append(f"# {title}")
    out.append("")
    out.append(f"_mode: {mode}_")
    out.append("")

    if include_toc:
        out.append("## Содержание")
        out.append("")
        for i, ch in enumerate(chapters, 1):
            out.append(f"{i}. {ch.title}")
        out.append("")

    for ch in chapters:
        out.append(f"## {ch.title}")
        out.append("")
        out.extend(ch.body_lines)
        out.append("")

    text = "\n".join(out).rstrip() + "\n"
    if include_stats:
        pages = estimate_pages(text)
        words = count_words(text)
        text = (
            text
            + "\n---\n\n"
            + f"_stats: chars={len(text)}, words={words}, pages={pages:.1f} (rough)_\n"
        )
    return text


def postprocess_compiled_markdown(text: str, manifest_path: pathlib.Path) -> str:
    # Keep the source Markdown simple and do small readability tweaks at compile time.
    # Currently this is only used for RU v2.
    if "ru_v2" not in manifest_path.as_posix():
        return text

    # Remove compile-mode marker from print-ready artifact (it is a technical build hint).
    text = re.sub(r"(?m)^_mode:\s*[^_]+_\s*$\n?\n?", "", text)

    # Add a small “cover” block under the top-level title, before the ToC.
    # This keeps the book self-contained even when exported as a single HTML/PDF.
    m = re.match(r"(?s)^(# .+?\n)(\n?)(##\s+Содержание\n)", text)
    if m:
        title_line = m.group(1).rstrip("\n")
        cover = (
            f"{title_line}\n\n"
            "_Операционная карта для диагностики и действий в сложных человеческих системах._\n\n"
            "<div style=\"page-break-after: always;\"></div>\n\n"
            "## Содержание\n"
        )
        text = cover + text[m.end(3) :]

    # Make mini-vignette labels more scannable (both in the format description and in the vignettes).
    # Matches:
    #   - Наблюдаемые входы:
    #   - `Наблюдаемые входы`:
    # but does not touch already-bolded forms like:
    #   - **Наблюдаемые входы:**
    labels = [
        "Наблюдаемые входы",
        "Минимальная операция",
        "Readout",
        "Цена/перенос цены",
        "Цена",
    ]
    for label in labels:
        pattern = rf"(?m)^-\s+`?{re.escape(label)}`?\s*:"
        text = re.sub(pattern, f"- **{label}:**", text)

    # Remove draft status markers from print-ready output.
    # Keep these in source files, but do not ship them in compiled artifacts.
    text = re.sub(r"(?m)^- Статус: черновик\.\s*$\n?", "", text)

    return text


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description="Compile RU book chapters into a single Markdown file.")
    parser.add_argument(
        "--manifest",
        type=pathlib.Path,
        default=pathlib.Path("docs/book/ru/manifest_ru.txt"),
        help="Path to manifest file listing chapters in order.",
    )
    parser.add_argument(
        "--out",
        type=pathlib.Path,
        default=pathlib.Path("docs/book/ru/_compiled.md"),
        help="Output Markdown path.",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Write compiled Markdown to stdout (equivalent to --out -).",
    )
    parser.add_argument(
        "--mode",
        choices=("draft", "print"),
        default="draft",
        help="draft: keep author notes; print: strip notes/admonitions and @draft blocks.",
    )
    parser.add_argument("--title", default="Книга (черновик сборки)", help="Book title for compiled output.")
    parser.add_argument("--no-toc", action="store_true", help="Do not include a simple table of contents.")
    parser.add_argument("--no-stats", action="store_true", help="Do not include rough word/page stats.")
    parser.add_argument(
        "--no-glossary",
        action="store_true",
        help="Exclude 01_terms.md even if present in manifest.",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Print per-chapter word/char stats to stderr.",
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Print report to stderr and exit (do not emit compiled Markdown).",
    )
    args = parser.parse_args(list(argv))

    manifest_path = args.manifest.resolve()
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    chapter_paths = load_manifest(manifest_path)
    chapters, warnings = build_book(
        chapter_paths,
        mode=args.mode,
        include_glossary=not args.no_glossary,
    )

    if args.report or args.report_only:
        print_report(chapters, mode=args.mode)
        if args.report_only:
            return 0

    compiled = render(
        chapters,
        title=args.title,
        mode=args.mode,
        include_toc=not args.no_toc,
        include_stats=not args.no_stats,
    )
    compiled = postprocess_compiled_markdown(compiled, manifest_path=manifest_path)

    if warnings:
        print("Warnings:", file=sys.stderr)
        for w in warnings:
            print(f"- {w}", file=sys.stderr)

    def write_stdout_utf8(payload: str) -> None:
        data = payload.encode("utf-8")

        # In some Windows setups (e.g. detached console / pythonw / certain Start-Process modes),
        # sys.stdout can be None or not expose a binary buffer.
        out = getattr(sys, "stdout", None)
        if out is None:
            os.write(1, data)
            return

        buf = getattr(out, "buffer", None)
        if buf is not None:
            buf.write(data)
            buf.flush()
            return

        out.write(payload)
        out.flush()

    if args.stdout or str(args.out) == "-":
        write_stdout_utf8(compiled)
        return 0

    out_path = args.out.resolve()
    try:
        out_path.write_text(compiled, encoding="utf-8")
    except PermissionError:
        print(
            f"PermissionError: cannot write to {out_path}. Writing to stdout instead.",
            file=sys.stderr,
        )
        print(
            "Tip: run with `--out -` and redirect: `python tools/compile_book_ru.py --mode draft --out - > docs/book/ru/_compiled.md`.",
            file=sys.stderr,
        )
        write_stdout_utf8(compiled)
        return 0

    print(f"Wrote: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
