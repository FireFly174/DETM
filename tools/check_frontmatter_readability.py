#!/usr/bin/env python3
from __future__ import annotations

import argparse
import pathlib
import re
import sys
from dataclasses import dataclass


SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
WORD_RE = re.compile(r"\S+", flags=re.UNICODE)
HEADING_RE = re.compile(r"^\s*#+\s")
LIST_RE = re.compile(r"^\s*[-*]\s|^\s*\d+\)\s")
CODE_FENCE_RE = re.compile(r"^\s*```")
FIRST_ACTION_RE = re.compile(
    r"(перв(ый|ого)\s+шаг|начни с|сделай\s+один\s+шаг|что делать первым шагом)",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class Limits:
    max_avg_sentence_words: float = 22.0
    max_long_sentences: int = 4
    long_sentence_words: int = 30
    max_paragraph_words: int = 140


def count_words(text: str) -> int:
    return len(WORD_RE.findall(text))


def extract_sentences(text: str) -> list[str]:
    parts = [x.strip() for x in SENTENCE_SPLIT_RE.split(text) if x.strip()]
    return parts


def extract_paragraphs(lines: list[str]) -> list[str]:
    paragraphs: list[str] = []
    buf: list[str] = []
    in_code = False
    for line in lines:
        if CODE_FENCE_RE.match(line):
            in_code = not in_code
            continue
        if in_code:
            continue
        if not line.strip():
            if buf:
                paragraphs.append(" ".join(buf))
                buf = []
            continue
        if HEADING_RE.match(line) or LIST_RE.match(line) or line.lstrip().startswith(">"):
            if buf:
                paragraphs.append(" ".join(buf))
                buf = []
            continue
        buf.append(line.strip())
    if buf:
        paragraphs.append(" ".join(buf))
    return paragraphs


def evaluate_file(path: pathlib.Path, limits: Limits) -> list[str]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    issues: list[str] = []

    sentences = extract_sentences(text)
    if sentences:
        sent_words = [count_words(s) for s in sentences]
        avg_sent = sum(sent_words) / len(sent_words)
        if avg_sent > limits.max_avg_sentence_words:
            issues.append(
                f"average sentence too long: {avg_sent:.1f} > {limits.max_avg_sentence_words:.1f}"
            )
        long_count = sum(1 for w in sent_words if w >= limits.long_sentence_words)
        if long_count > limits.max_long_sentences:
            issues.append(
                f"too many long sentences: {long_count} > {limits.max_long_sentences} "
                f"(threshold={limits.long_sentence_words} words)"
            )

    paragraphs = extract_paragraphs(lines)
    if paragraphs:
        max_para = max(count_words(p) for p in paragraphs)
        if max_para > limits.max_paragraph_words:
            issues.append(
                f"paragraph too long: {max_para} > {limits.max_paragraph_words} words"
            )

    require_first_action = path.name in {
        "00_start_here.src.md",
        "00_quickstart.src.md",
        "05_first_aid.src.md",
    }
    if require_first_action and not FIRST_ACTION_RE.search(text):
        issues.append("missing explicit first-action cue (e.g. 'первый шаг'/'начни с')")

    return issues


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Readability check for RU v2 frontmatter onboarding files."
    )
    parser.add_argument(
        "--book-root",
        type=pathlib.Path,
        default=pathlib.Path("docs/book/ru_v2"),
        help="Path to RU v2 book root.",
    )
    args = parser.parse_args()

    files = [
        "00_frontmatter/00_start_here.src.md",
        "00_frontmatter/00_quickstart.src.md",
        "00_frontmatter/01_thesis.src.md",
        "00_frontmatter/03_how_to_read.src.md",
        "00_frontmatter/05_first_aid.src.md",
    ]
    limits = Limits()
    root = args.book_root.resolve()

    failures = 0
    for rel in files:
        path = root / rel
        if not path.exists():
            print(f"[ERR] missing file: {path}")
            failures += 1
            continue
        issues = evaluate_file(path, limits)
        if not issues:
            print(f"[OK] {rel}")
            continue
        failures += 1
        print(f"[FAIL] {rel}")
        for issue in issues:
            print(f"  - {issue}")

    if failures:
        print(f"Readability check failed: {failures} file(s)")
        return 1
    print("Readability check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
