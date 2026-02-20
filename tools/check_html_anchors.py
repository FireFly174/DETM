#!/usr/bin/env python3
from __future__ import annotations

import argparse
import pathlib
import sys
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit


@dataclass(frozen=True)
class Ref:
    fragment: str
    line: int
    col: int


class AnchorParser(HTMLParser):
    def __init__(self, *, current_name: str) -> None:
        super().__init__(convert_charrefs=True)
        self.current_name = current_name
        self.ids: set[str] = set()
        self.duplicate_ids: set[str] = set()
        self.refs: list[Ref] = []

    def _add_id(self, value: str) -> None:
        v = value.strip()
        if not v:
            return
        if v in self.ids:
            self.duplicate_ids.add(v)
        self.ids.add(v)

    def _add_ref(self, href: str) -> None:
        href = href.strip()
        if not href:
            return
        parts = urlsplit(href)

        # Only check same-document refs:
        # - "#frag"
        # - "this_file.html#frag"
        if not parts.fragment:
            return
        if parts.scheme or parts.netloc:
            return
        if parts.path:
            p = pathlib.Path(parts.path)
            if p.name and p.name != self.current_name:
                return

        frag = unquote(parts.fragment).strip()
        if not frag:
            return
        line, col = self.getpos()
        self.refs.append(Ref(fragment=frag, line=line, col=col))

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = {k.lower(): (v or "") for k, v in attrs}
        if "id" in attrs_map:
            self._add_id(attrs_map["id"])
        if tag.lower() == "a":
            if "name" in attrs_map:
                self._add_id(attrs_map["name"])
            if "href" in attrs_map:
                self._add_ref(attrs_map["href"])


def check_file(path: pathlib.Path, *, show_missing_limit: int) -> tuple[int, int, int]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    parser = AnchorParser(current_name=path.name)
    parser.feed(text)
    parser.close()

    missing = [r for r in parser.refs if r.fragment not in parser.ids]
    print(
        f"{path.as_posix()}: ids={len(parser.ids)} refs={len(parser.refs)} "
        f"missing={len(missing)} duplicates={len(parser.duplicate_ids)}"
    )

    if parser.duplicate_ids:
        dups = sorted(parser.duplicate_ids)
        print("  duplicate ids:")
        for d in dups[:show_missing_limit]:
            print(f"    - {d}")
        if len(dups) > show_missing_limit:
            print(f"    ... +{len(dups) - show_missing_limit} more")

    if missing:
        print("  missing refs:")
        for r in missing[:show_missing_limit]:
            print(f"    - #{r.fragment} at {path.as_posix()}:{r.line}:{r.col}")
        if len(missing) > show_missing_limit:
            print(f"    ... +{len(missing) - show_missing_limit} more")

    return len(parser.ids), len(parser.refs), len(missing)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Validate same-document anchor links in HTML files."
    )
    parser.add_argument("html", nargs="+", help="HTML files to validate")
    parser.add_argument(
        "--show-limit",
        type=int,
        default=20,
        help="Maximum number of missing refs/duplicates to print per file",
    )
    args = parser.parse_args(argv)

    total_missing = 0
    for raw in args.html:
        p = pathlib.Path(raw)
        if not p.exists():
            print(f"{p.as_posix()}: missing file", file=sys.stderr)
            total_missing += 1
            continue
        _, _, missing = check_file(p, show_missing_limit=max(1, args.show_limit))
        total_missing += missing

    if total_missing > 0:
        print(f"FAIL: missing anchors total={total_missing}", file=sys.stderr)
        return 1
    print("OK: no missing anchors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
