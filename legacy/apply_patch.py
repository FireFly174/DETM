#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from pathlib import Path

def read_patch(path: Path) -> list[dict]:
    blocks = []
    cur = None
    buf = []

    def flush():
        nonlocal cur, buf
        if cur:
            cur["content"] = "\n".join(buf).rstrip() + "\n"
            blocks.append(cur)
        cur, buf = None, []

    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("=== CREATE FILE ==="):
            flush()
            cur = {"type": "create"}
        elif line.startswith("=== MODIFY FILE ==="):
            flush()
            cur = {"type": "modify"}
        elif line.startswith("=== END PATCH ==="):
            flush()
            break
        elif line.strip() == "---":
            continue
        elif cur is not None and ":" in line and not buf:
            k, v = line.split(":", 1)
            cur[k.strip()] = v.strip()
        else:
            buf.append(line)

    flush()
    return blocks


def apply_patch(blocks: list[dict], root: Path):
    for b in blocks:
        path = root / b["path"]

        if b["type"] == "create":
            print(f"[CREATE] {path}")
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists():
                print(f"  ! exists, skipped")
                continue
            path.write_text(b["content"], encoding="utf-8")

        elif b["type"] == "modify":
            if not path.exists():
                print(f"[ERROR] file not found: {path}")
                continue

            text = path.read_text(encoding="utf-8")

            mode = b.get("mode", "append")

            if mode == "append":
                anchor = b["anchor"]
                idx = text.find(anchor)
                if idx < 0:
                    print(f"[ERROR] anchor not found in {path}")
                    continue
                insert_at = idx + len(anchor)
                text = text[:insert_at] + "\n\n" + b["content"] + text[insert_at:]

            elif mode == "replace_block":
                a = b["anchor_start"]
                z = b["anchor_end"]
                i1 = text.find(a)
                i2 = text.find(z)
                if i1 < 0 or i2 < 0 or i2 <= i1:
                    print(f"[ERROR] block anchors not found in {path}")
                    continue
                i2 += len(z)
                text = text[:i1] + b["content"] + text[i2:]

            else:
                print(f"[ERROR] unknown mode {mode}")
                continue

            path.write_text(text, encoding="utf-8")
            print(f"[MODIFY] {path}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python apply_patch.py patch.txt")
        sys.exit(1)

    patch_path = Path(sys.argv[1])
    root = Path("../../LMU").resolve()

    blocks = read_patch(patch_path)
    apply_patch(blocks, root)
    print("\n[OK] Patch applied")

if __name__ == "__main__":
    main()
