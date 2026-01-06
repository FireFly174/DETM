#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Bundle a Python project into a single text file for sharing/review.

Usage:
  python bundle_project.py --root .
  python bundle_project.py --root . --out DETM_bundle.txt
  python bundle_project.py --check

By default includes: *.py, *.json, *.yml, *.yaml, *.toml, *.ini, *.md
Excludes: venv, .venv, __pycache__, .git, dist, build, .mypy_cache, .pytest_cache, node_modules

This script also supports a "peer bundle link" workflow for working with two
repos (e.g. DETM <-> ACGS) in the same parent folder:
- generates `<this_repo>_bundle.txt` in the current repo
- creates/updates `<peer_repo>_bundle.txt` as a symlink (or hardlink fallback)
  pointing to the peer repo bundle file.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime

DEFAULT_INCLUDE = [
    "*.py",
    "*.json",
    "*.yml",
    "*.yaml",
    "*.toml",
    "*.ini",
    "*.md",
    '*.elf',
    '*.bin',
    '*.map',
    '*.sym',
    #'*.c',
    #'*.h',
    #'*.cpp',
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
    'bundle_project.py',
    'PD51',
    'Untitled Project.si4project',
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


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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


def default_bundle_path(root: Path, out: str | None) -> Path:
    if out is None:
        return root / f"{root.name}_bundle.txt"
    return Path(out).resolve()


def guess_peer_root(root: Path) -> Path | None:
    env_peer = os.environ.get("BUNDLE_PEER_ROOT")
    if env_peer:
        candidate = Path(env_peer).expanduser()
        if candidate.exists():
            return candidate.resolve()

    mapping = {"DETM": "ACGS", "ACGS": "DETM"}
    peer_name = mapping.get(root.name)
    if peer_name:
        candidate = root.parent / peer_name
        if candidate.exists():
            return candidate.resolve()
    return None


def link_relation(link_path: Path, target_path: Path) -> str:
    if link_path.is_symlink():
        try:
            if link_path.resolve() == target_path.resolve():
                return "symlink"
        except OSError:
            return "broken_symlink"

    try:
        st_link = link_path.stat()
        st_target = target_path.stat()
        if (st_link.st_ino, st_link.st_dev) == (st_target.st_ino, st_target.st_dev):
            return "hardlink"
    except OSError:
        return "missing"

    try:
        if sha256_file(link_path) == sha256_file(target_path):
            return "copy"
    except OSError:
        return "missing"

    return "different"


def ensure_link(link_path: Path, target_path: Path, mode: str) -> str:
    """Ensure link_path points to target_path.

    mode: auto | symlink | hardlink | copy
    """

    if link_path.exists() or link_path.is_symlink():
        link_path.unlink()

    mode = str(mode).strip().lower() or "auto"
    if mode not in {"auto", "symlink", "hardlink", "copy"}:
        raise ValueError(f"Unsupported link mode: {mode}")

    if mode in {"auto", "symlink"}:
        try:
            rel_target = os.path.relpath(target_path, start=link_path.parent)
            link_path.symlink_to(rel_target)
            return "symlink"
        except OSError:
            if mode == "symlink":
                raise

    if mode in {"auto", "hardlink"}:
        try:
            os.link(target_path, link_path)
            return "hardlink"
        except OSError:
            if mode == "hardlink":
                raise

    shutil.copy2(target_path, link_path)
    return "copy"


def _git_tracked_bundles(root: Path) -> list[str]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0 or proc.stdout.strip() != "true":
            return []
    except FileNotFoundError:
        return []

    ls = subprocess.run(
        ["git", "-C", str(root), "ls-files"],
        check=False,
        capture_output=True,
        text=True,
    )
    if ls.returncode != 0:
        return []

    tracked = []
    for line in ls.stdout.splitlines():
        name = line.strip().replace("\\", "/")
        if fnmatch.fnmatch(name, "*_bundle.txt"):
            tracked.append(line.strip())
    return tracked


def check_setup(root: Path, out_path: Path, peer_root: Path | None) -> int:
    ok = True

    if not out_path.exists():
        print(f"[ERR] missing local bundle: {out_path}")
        ok = False
    else:
        print(f"[OK] local bundle: {out_path}")

    tracked = _git_tracked_bundles(root)
    if tracked:
        ok = False
        print("[ERR] bundle files must be local-only; these are tracked by git:")
        for name in tracked:
            print(f"  - {name}")
        print("Fix: `git rm --cached <file>` and keep it ignored by .gitignore.")

    if peer_root is None:
        print("[WARN] peer repo not found (set --peer-root or BUNDLE_PEER_ROOT).")
        return 0 if ok else 1

    peer_bundle = peer_root / f"{peer_root.name}_bundle.txt"
    peer_link = root / peer_bundle.name

    if not peer_bundle.exists():
        print(f"[WARN] missing peer bundle (generate it in peer repo): {peer_bundle}")
        return 0 if ok else 1

    if not (peer_link.exists() or peer_link.is_symlink()):
        print(f"[WARN] missing peer link in this repo: {peer_link}")
        return 0 if ok else 1

    relation = link_relation(peer_link, peer_bundle)
    if relation in {"symlink", "hardlink"}:
        print(f"[OK] peer link ({relation}): {peer_link} -> {peer_bundle}")
    elif relation == "copy":
        print(f"[WARN] peer bundle is a copy, not a link: {peer_link}")
    else:
        ok = False
        print(f"[ERR] peer bundle differs from target: {peer_link} ({relation})")

    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".", help="Project root directory")
    ap.add_argument(
        "--out",
        default=None,
        help="Output bundle file (default: <project_name>_bundle.txt)",
    )
    ap.add_argument(
        "--peer-root",
        default=None,
        help="Path to peer repo root (default: auto-detect sibling or $BUNDLE_PEER_ROOT)",
    )
    ap.add_argument(
        "--link-peer",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Create/update <peer_repo>_bundle.txt link in this repo (default: enabled)",
    )
    ap.add_argument(
        "--link-mode",
        choices=["auto", "symlink", "hardlink", "copy"],
        default="auto",
        help="How to create peer bundle link (default: auto)",
    )
    ap.add_argument(
        "--check",
        action="store_true",
        help="Check bundle/link setup and exit (no bundle generation)",
    )
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
    out_path = default_bundle_path(root, args.out)

    peer_root: Path | None = None
    if args.peer_root is not None:
        candidate = Path(args.peer_root).expanduser()
        if candidate.exists():
            peer_root = candidate.resolve()
    if peer_root is None:
        peer_root = guess_peer_root(root)

    if args.check:
        return check_setup(root, out_path, peer_root)

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

    if args.link_peer and peer_root is not None:
        peer_bundle = peer_root / f"{peer_root.name}_bundle.txt"
        peer_link = root / peer_bundle.name
        if peer_bundle.exists():
            used = ensure_link(peer_link, peer_bundle, args.link_mode)
            print(f"[OK] Peer bundle ({used}): {peer_link} -> {peer_bundle}")
        else:
            print(f"[WARN] Peer bundle not found, cannot link: {peer_bundle}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
