#!/usr/bin/env python3
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Theme:
    code: str  # T1..T7
    title: str


@dataclass(frozen=True)
class Action:
    code: str  # L3-C4
    title: str


ROOT = Path(__file__).resolve().parents[1]
BOOK = ROOT / "docs" / "book" / "ru_v2"
APPENDIX = BOOK / "90_appendix"

TERMS_PATH = APPENDIX / "01_terms.md"
CASES_PATH = APPENDIX / "02_case_registry.md"

OUT_NAV = APPENDIX / "03_navigation.md"
OUT_INDEX = APPENDIX / "04_index.md"


TERMS_HEADING_RE = re.compile(r"^##\s+(.*\S)\s*$")
THEME_RE = re.compile(r"^###\s+(T\d+):\s+(.*\S)\s*$")
ACTION_RE = re.compile(r"^###\s+(L[0-5]-C\d+):\s+(.*\S)\s*$")
SCENE_RE = re.compile(r"^###\s+(S[1-5]):\s+(.*\S)\s*$")
SCENE_THEME_RE = re.compile(r"^####\s+(S[1-5]/T[1-7]):\s+(.*\S)\s*$")


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def extract_terms(lines: list[str]) -> list[str]:
    out: list[str] = []
    for line in lines:
        m = TERMS_HEADING_RE.match(line)
        if not m:
            continue
        title = m.group(1).strip()
        out.append(title)
    return out


def extract_themes(lines: list[str]) -> list[Theme]:
    out: list[Theme] = []
    for line in lines:
        m = THEME_RE.match(line)
        if not m:
            continue
        out.append(Theme(code=m.group(1), title=m.group(2)))
    return out


def extract_actions(lines: list[str]) -> list[Action]:
    out: list[Action] = []
    for line in lines:
        m = ACTION_RE.match(line)
        if not m:
            continue
        out.append(Action(code=m.group(1), title=m.group(2)))
    return out


def extract_scenes(lines: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in lines:
        m = SCENE_RE.match(line)
        if not m:
            continue
        out[m.group(1)] = m.group(2)
    return out


def extract_scene_themes(lines: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in lines:
        m = SCENE_THEME_RE.match(line)
        if not m:
            continue
        out[m.group(1)] = m.group(2)
    return out


def render_navigation(
    scenes: dict[str, str],
    themes: list[Theme],
    scene_themes: dict[str, str],
    actions: list[Action],
) -> str:
    s_order = ["S1", "S2", "S3", "S4", "S5"]
    t_order = [f"T{i}" for i in range(1, 8)]

    out: list[str] = []
    out.append('<a id="nav-cheatsheet"></a>')
    out.append("# Навигационная шпаргалка (S-T-C) (v2, черновик)")
    out.append("")
    out.append("Файл для быстрого цифрового и PDF-чтения: вместо длинных ссылок — короткие коды.")
    out.append("")
    out.append("## Как пользоваться")
    out.append("")
    out.append("1) Найди симптом в блоке ниже.")
    out.append("2) Возьми тему `T` и сцену `S`.")
    out.append("3) Найди первый оператор `Lx-Cn` в [реестре ситуаций](#case-registry).")
    out.append("4) Проверь ход по readout через `24h/72h`.")
    out.append("")
    out.append("## Симптом -> первый ход -> тест readout")
    out.append("")
    out.append("- «Любой выбор не меняет траекторию»")
    out.append("  Первый ход: `L1-C2` -> `L1-C5`.")
    out.append("  Тест: появился ли стабильный readout, меняющий следующий шаг.")
    out.append("")
    out.append("- «Метрики растут, а реальность нет»")
    out.append("  Первый ход: `L3-C1` или `L3-C6`.")
    out.append("  Тест: перестали ли решения приниматься по витринным метрикам.")
    out.append("")
    out.append("- «Спор о смыслах/осях»")
    out.append("  Первый ход: `L3-C7`.")
    out.append("  Тест: зафиксированы ли общие оси и критерии проверяемости.")
    out.append("")
    out.append("- «Цель размыта, нет следующего шага»")
    out.append("  Первый ход: `L1-C2`.")
    out.append("  Тест: определен ли один ближайший шаг и его readout.")
    out.append("")
    out.append("- «Пожарность и каскад сбоев»")
    out.append("  Первый ход: `L0-C1`, затем `L0-C5` при необходимости.")
    out.append("  Тест: локализован ли каскад в пределах одного контура.")
    out.append("")
    out.append("## Сцены (S1-S5)")
    out.append("")
    scene_fallback = {
        "S1": "человек",
        "S2": "семья/близкие",
        "S3": "общество/игры",
        "S4": "организация",
        "S5": "государство/институты",
    }
    for s in s_order:
        title = scenes.get(s) or scene_fallback[s]
        out.append(f"- `{s}` — {title}")
    out.append("")
    out.append("## Темы (T1-T7)")
    out.append("")
    for t in t_order:
        theme = next((x for x in themes if x.code == t), None)
        title = theme.title if theme is not None else ""
        # Keep all Sx/Ty shortcuts explicit; they are core navigation affordances.
        codes = [f"`{s}/{t}`" for s in s_order]
        # If case registry parsing found a subset, prefer it only when non-empty.
        parsed_codes = []
        for s in s_order:
            key = f"{s}/{t}"
            if key in scene_themes:
                parsed_codes.append(f"`{key}`")
        suffix = ", ".join(parsed_codes or codes)
        out.append(f"- `{t}` {title}: {suffix}".rstrip())
    out.append("")
    out.append("## Действия (Lx-Cn)")
    out.append("")
    # Group by Lx
    by_level: dict[str, list[Action]] = {}
    for a in actions:
        level = a.code.split("-")[0]
        by_level.setdefault(level, []).append(a)
    for level in ["L0", "L1", "L2", "L3", "L4", "L5"]:
        items = sorted(by_level.get(level, []), key=lambda x: x.code)
        if not items:
            continue
        out.append(f"### {level}")
        out.append("")
        for a in items:
            out.append(f"- `{a.code}` — {a.title}")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def render_index(terms: list[str], themes: list[Theme], actions: list[Action]) -> str:
    out: list[str] = []
    out.append("# Индекс (термины и паттерны) (v2, черновик)")
    out.append("")
    out.append("Индекс нужен не для «правильности», а для скорости: вспомнить формулировку и найти место в тексте через поиск по коду.")
    out.append("")
    out.append("## Термины")
    out.append("")
    out.append("Источник: раздел «Термины» в этой книге.")
    out.append("")
    for term in sorted(set(terms), key=lambda s: s.casefold()):
        out.append(f"- {term}")
    out.append("")
    out.append("## Темы (T1–T7)")
    out.append("")
    out.append("Источник: раздел `Реестр ситуаций` в этой книге (`#case-registry`, блок «Сквозные темы»).")
    out.append("")
    for th in themes:
        out.append(f"- `{th.code}` — {th.title}")
    out.append("")
    out.append("## Действия (Lx-Cn)")
    out.append("")
    out.append("Источник: раздел `Реестр ситуаций` в этой книге (`#case-registry`, блоки «Действия уровня …»).")
    out.append("")
    for a in sorted(actions, key=lambda x: (x.code.split('-')[0], x.code)):
        out.append(f"- `{a.code}` — {a.title}")
    out.append("")
    return "\n".join(out).rstrip() + "\n"


def write_pair(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    src_path = path.with_suffix(".src.md")
    src_path.write_text(content, encoding="utf-8")


def main() -> int:
    if not TERMS_PATH.exists():
        raise FileNotFoundError(f"Missing: {TERMS_PATH}")
    if not CASES_PATH.exists():
        raise FileNotFoundError(f"Missing: {CASES_PATH}")

    terms = extract_terms(read_lines(TERMS_PATH))
    case_lines = read_lines(CASES_PATH)
    themes = extract_themes(case_lines)
    actions = extract_actions(case_lines)
    scenes = extract_scenes(case_lines)
    scene_themes = extract_scene_themes(case_lines)

    nav = render_navigation(scenes=scenes, themes=themes, scene_themes=scene_themes, actions=actions)
    idx = render_index(terms=terms, themes=themes, actions=actions)

    write_pair(OUT_NAV, nav)
    write_pair(OUT_INDEX, idx)
    print(f"Wrote: {OUT_NAV}")
    print(f"Wrote: {OUT_NAV.with_suffix('.src.md')}")
    print(f"Wrote: {OUT_INDEX}")
    print(f"Wrote: {OUT_INDEX.with_suffix('.src.md')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
