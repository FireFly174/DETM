#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Bundle a Python project into a single text file for sharing/review.

Usage:
  python bundle_project.py --root . --out DETM_bundle.txt

By default includes: *.py, *.json, *.yml, *.yaml, *.toml, *.ini, *.md
Excludes: venv, .venv, __pycache__, .git, dist, build, .mypy_cache, .pytest_cache, node_modules
"""

from __future__ import annotations

import argparse
from pathlib import Path
import fnmatch
import os
import sys
import hashlib
from datetime import datetime

DEFAULT_INCLUDE = [
    "*.py",
    "*.json",
    "*.yml",
    "*.yaml",
    "*.toml",
    "*.ini",
    "*.md",
]

DEFAULT_EXCLUDE_DIRS = {
    ".git",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".idea",
    ".vscode",
    "venv",
    ".venv",
    "env",
    ".env",
    "build",
    "dist",
    "node_modules",
}

DEFAULT_EXCLUDE_FILES = {
    ".DS_Store",
}


def is_excluded_dir(path: Path, exclude_dirs: set[str]) -> bool:
    parts = {p.name for p in path.parents} | {path.name}
    return any(d in parts for d in exclude_dirs)


def matches_any(name: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(name, p) for p in patterns)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def read_text_safely(p: Path) -> str:
    # Try UTF-8, then fallback.
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return p.read_text(encoding="utf-8", errors="replace")


def build_tree(root: Path, include: list[str], exclude_dirs: set[str]) -> str:
    lines: list[str] = []
    root = root.resolve()
    for dirpath, dirnames, filenames in os.walk(root):
        dpath = Path(dirpath)
        # prune excluded dirs
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]

        rel_dir = dpath.relative_to(root)
        indent = "  " * (len(rel_dir.parts) if rel_dir.parts != (".",) else 0)
        if str(rel_dir) != ".":
            lines.append(f"{indent}{rel_dir}/")

        for fn in sorted(filenames):
            if fn in DEFAULT_EXCLUDE_FILES:
                continue
            if matches_any(fn, include):
                lines.append(f"{indent}  {fn}")
    return "\n".join(lines)


def collect_files(root: Path, include: list[str], exclude_dirs: set[str]) -> list[Path]:
    root = root.resolve()
    out: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dpath = Path(dirpath)
        dirnames[:] = [d for d in dirnames if d not in exclude_dirs]

        for fn in filenames:
            if fn in DEFAULT_EXCLUDE_FILES:
                continue
            if matches_any(fn, include):
                p = dpath / fn
                out.append(p)
    return sorted(out, key=lambda p: str(p).lower())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="Project root directory")
    ap.add_argument("--out", default="DETM_bundle.txt", help="Output bundle file")
    ap.add_argument(
        "--include",
        nargs="*",
        default=DEFAULT_INCLUDE,
        help="Glob patterns to include (default: common project text files)",
    )
    ap.add_argument(
        "--exclude-dir",
        nargs="*",
        default=sorted(DEFAULT_EXCLUDE_DIRS),
        help="Directory names to exclude",
    )
    ap.add_argument(
        "--max-bytes",
        type=int,
        default=2_000_000,
        help="Skip files larger than this size in bytes (default 2MB)",
    )
    args = ap.parse_args()

    root = Path(args.root).resolve()
    out_path = Path(args.out).resolve()

    exclude_dirs = set(args.exclude_dir)
    include = list(args.include)

    files = collect_files(root, include, exclude_dirs)

    header = []
    header.append("PROJECT BUNDLE (for review)")
    header.append(f"root: {root}")
    header.append(f"generated_at: {datetime.now().isoformat(timespec='seconds')}")
    header.append(f"include: {include}")
    header.append(f"exclude_dirs: {sorted(exclude_dirs)}")
    header.append("")
    header.append("TREE:")
    header.append(build_tree(root, include, exclude_dirs))
    header.append("")
    header.append("=" * 80)
    header.append("FILES:")
    header.append("=" * 80)
    header.append("")

    chunks: list[str] = ["\n".join(header)]

    for p in files:
        rel = p.relative_to(root)
        size = p.stat().st_size
        if size > args.max_bytes:
            chunks.append(
                f"\n\n--- FILE: {rel} ---\n"
                f"(skipped: {size} bytes > max_bytes={args.max_bytes})\n"
            )
            continue

        text = read_text_safely(p)
        digest = sha256_text(text)[:16]

        chunks.append(
            "\n\n"
            + "-" * 80
            + f"\nFILE: {rel}\nSIZE: {size} bytes\nSHA256_16: {digest}\n"
            + "-" * 80
            + "\n"
            + text
            + "\n"
        )

    out_path.write_text("".join(chunks), encoding="utf-8")
    print(f"[OK] Wrote bundle: {out_path}")
    print(f"[OK] Files included: {len(files)}")


if __name__ == "__main__":
    sys.exit(main())
