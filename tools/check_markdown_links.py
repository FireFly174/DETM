#!/usr/bin/env python3
from __future__ import annotations

import argparse
import pathlib
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from html import unescape
from urllib.parse import unquote, urlsplit


LINK_RE = re.compile(r'(?P<image>!)?\[[^\]]*]\((?P<dest>[^)]+)\)')
EXPLICIT_ID_RE = re.compile(r'<a\s+(?:id|name)\s*=\s*"([^"]+)"', re.IGNORECASE)
FENCE_RE = re.compile(r"^\s*(```|~~~)")
HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.*)$")


@dataclass(frozen=True)
class LinkIssue:
    file: pathlib.Path
    line: int
    kind: str
    detail: str


def _slugify_heading(text: str) -> str:
    text = unescape(text).strip().lower()
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[^\w\s\-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s\-]+", "-", text, flags=re.UNICODE).strip("-")
    return text


def extract_md_anchors(path: pathlib.Path) -> tuple[set[str], list[str]]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    anchors: set[str] = set()
    duplicates: list[str] = []
    counter: Counter[str] = Counter()

    for m in EXPLICIT_ID_RE.finditer(text):
        anchor = m.group(1).strip()
        if not anchor:
            continue
        if anchor in anchors:
            duplicates.append(anchor)
        anchors.add(anchor)

    in_fence = False
    for raw_line in text.splitlines():
        if FENCE_RE.match(raw_line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        hm = HEADING_RE.match(raw_line)
        if not hm:
            continue
        title = hm.group(2).strip()
        title = re.sub(r"\s+#+\s*$", "", title)
        explicit = re.search(r"\s*\{#([A-Za-z0-9\-_:./]+)\}\s*$", title)
        if explicit:
            anchor = explicit.group(1).strip()
            title = title[: explicit.start()].strip()
            if anchor in anchors:
                duplicates.append(anchor)
            anchors.add(anchor)
            continue
        slug = _slugify_heading(title)
        if not slug:
            continue
        idx = counter[slug]
        counter[slug] += 1
        anchor = slug if idx == 0 else f"{slug}-{idx}"
        if anchor in anchors:
            duplicates.append(anchor)
        anchors.add(anchor)

    return anchors, duplicates


def extract_html_anchors(path: pathlib.Path) -> tuple[set[str], list[str]]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    anchors: set[str] = set()
    duplicates: list[str] = []
    for m in re.finditer(r'\s(?:id|name)="([^"]+)"', text):
        anchor = m.group(1).strip()
        if not anchor:
            continue
        if anchor in anchors:
            duplicates.append(anchor)
        anchors.add(anchor)
    return anchors, duplicates


def parse_link_dest(raw_dest: str) -> str:
    dest = raw_dest.strip()
    if not dest:
        return ""
    if dest.startswith("<"):
        end = dest.find(">")
        if end != -1:
            return dest[1:end].strip()
    return dest.split()[0].strip()


def is_external(dest: str) -> bool:
    if not dest:
        return True
    parts = urlsplit(dest)
    if parts.scheme:
        return True
    if parts.netloc:
        return True
    if dest.startswith("//"):
        return True
    return False


def collect_links(path: pathlib.Path) -> list[tuple[int, str]]:
    links: list[tuple[int, str]] = []
    in_fence = False
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    for lineno, line in enumerate(lines, start=1):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if line.startswith("    ") or line.startswith("\t"):
            continue
        for m in LINK_RE.finditer(line):
            if m.group("image"):
                continue
            dest = parse_link_dest(m.group("dest"))
            if not dest or is_external(dest):
                continue
            links.append((lineno, dest))
    return links


def load_anchor_set(target: pathlib.Path, cache: dict[pathlib.Path, set[str]]) -> tuple[set[str], list[str]]:
    if target in cache:
        return cache[target], []
    ext = target.suffix.lower()
    if ext in {".md", ".markdown", ".mdx", ""}:
        anchors, duplicates = extract_md_anchors(target)
    elif ext in {".html", ".htm"}:
        anchors, duplicates = extract_html_anchors(target)
    else:
        anchors, duplicates = set(), []
    cache[target] = anchors
    return anchors, duplicates


def check_files(files: list[pathlib.Path]) -> list[LinkIssue]:
    issues: list[LinkIssue] = []
    anchor_cache: dict[pathlib.Path, set[str]] = {}
    duplicate_anchors: dict[pathlib.Path, list[str]] = defaultdict(list)

    for file in files:
        if not file.exists():
            issues.append(LinkIssue(file=file, line=0, kind="missing-file", detail="input file not found"))
            continue

        links = collect_links(file)
        for lineno, dest in links:
            target_raw, _, frag_raw = dest.partition("#")
            target_path = file if not target_raw else (file.parent / unquote(target_raw)).resolve()
            frag = unquote(frag_raw).strip()

            if target_raw and not target_path.exists():
                issues.append(
                    LinkIssue(
                        file=file,
                        line=lineno,
                        kind="missing-target",
                        detail=f"{dest} -> {target_path.as_posix()} does not exist",
                    )
                )
                continue

            if frag:
                anchors, dups = load_anchor_set(target_path, anchor_cache)
                if dups:
                    duplicate_anchors[target_path].extend(dups)
                if frag not in anchors:
                    issues.append(
                        LinkIssue(
                            file=file,
                            line=lineno,
                            kind="missing-anchor",
                            detail=f"{dest} -> #{frag} not found in {target_path.as_posix()}",
                        )
                    )

    for target, dups in duplicate_anchors.items():
        uniq = sorted(set(dups))
        for anchor in uniq:
            issues.append(
                LinkIssue(
                    file=target,
                    line=0,
                    kind="duplicate-anchor",
                    detail=f'duplicate anchor "{anchor}"',
                )
            )

    return issues


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Validate local markdown links and anchors."
    )
    parser.add_argument("paths", nargs="+", help="Markdown files to validate")
    args = parser.parse_args(argv)

    files = [pathlib.Path(p).resolve() for p in args.paths]
    issues = check_files(files)

    if issues:
        print(f"FAIL: issues={len(issues)}", file=sys.stderr)
        for issue in issues:
            loc = f"{issue.file.as_posix()}:{issue.line}" if issue.line else issue.file.as_posix()
            print(f"- [{issue.kind}] {loc} -> {issue.detail}", file=sys.stderr)
        return 1

    for file in files:
        print(f"{file.as_posix()}: OK")
    print("OK: markdown links/anchors valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
