#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import datetime as dt
import fnmatch
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass
class FileMetrics:
    path: str
    module: str
    layer: str
    file_loc: int
    max_function_loc: int
    max_class_methods: int
    import_count: int
    max_nesting: int
    fan_out: int


def read_policy(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("policy file must be a mapping")
    return data


def build_module_name(path: Path, root: Path) -> str:
    rel = path.relative_to(root).with_suffix("")
    return ".".join(rel.parts)


def resolve_relative_import(module: str, imported: str | None, level: int) -> str:
    if level <= 0:
        return imported or ""
    parts = module.split(".")
    base = parts[:-level]
    if imported:
        base.extend(imported.split("."))
    return ".".join(base)


def max_nesting_depth(tree: ast.AST) -> int:
    nesting_nodes = (
        ast.If,
        ast.For,
        ast.AsyncFor,
        ast.While,
        ast.With,
        ast.AsyncWith,
        ast.Try,
        ast.Match,
    )

    def walk(node: ast.AST, depth: int) -> int:
        max_depth = depth
        for child in ast.iter_child_nodes(node):
            next_depth = depth + 1 if isinstance(child, nesting_nodes) else depth
            max_depth = max(max_depth, walk(child, next_depth))
        return max_depth

    return walk(tree, 0)


def classify_layer(path: str, layer_patterns: list[dict[str, Any]]) -> str:
    norm = path.replace("\\", "/")
    for item in layer_patterns:
        layer = item["layer"]
        patterns = item.get("patterns", [])
        for pattern in patterns:
            if fnmatch.fnmatch(norm, pattern):
                return layer
    return "unknown"


def resolve_to_known_module(raw: str, known_modules: set[str]) -> str | None:
    if not raw:
        return None
    parts = raw.split(".")
    for i in range(len(parts), 0, -1):
        cand = ".".join(parts[:i])
        if cand in known_modules:
            return cand
    return None


def find_cycles(edges: dict[str, set[str]]) -> list[list[str]]:
    index = 0
    stack: list[str] = []
    indices: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    on_stack: set[str] = set()
    sccs: list[list[str]] = []

    def strongconnect(v: str) -> None:
        nonlocal index
        indices[v] = index
        lowlink[v] = index
        index += 1
        stack.append(v)
        on_stack.add(v)

        for w in edges.get(v, set()):
            if w not in indices:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif w in on_stack:
                lowlink[v] = min(lowlink[v], indices[w])

        if lowlink[v] == indices[v]:
            scc: list[str] = []
            while True:
                w = stack.pop()
                on_stack.remove(w)
                scc.append(w)
                if w == v:
                    break
            if len(scc) > 1:
                sccs.append(sorted(scc))

    for node in edges.keys():
        if node not in indices:
            strongconnect(node)

    return sorted(sccs, key=lambda c: (len(c), c), reverse=True)


def scan_python_files(roots: list[Path]) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        files.extend(sorted([p for p in root.rglob("*.py") if p.is_file() and "__pycache__" not in p.parts]))
    return files


def analyze(
    repo_root: Path,
    roots: list[Path],
    policy: dict[str, Any],
) -> dict[str, Any]:
    limits = policy["limits"]
    layer_patterns = policy["layer_patterns"]
    allowed_dependencies = policy["allowed_dependencies"]

    py_files = scan_python_files(roots)
    module_by_file: dict[Path, str] = {}
    known_modules: set[str] = set()
    for f in py_files:
        mod = build_module_name(f, repo_root)
        module_by_file[f] = mod
        known_modules.add(mod)

    metrics: list[FileMetrics] = []
    edges: dict[str, set[str]] = defaultdict(set)
    violations: list[dict[str, Any]] = []

    for f in py_files:
        text = f.read_text(encoding="utf-8", errors="ignore")
        lines = text.splitlines()
        loc = len(lines)
        try:
            tree = ast.parse(text, filename=str(f))
        except SyntaxError as e:
            violations.append(
                {
                    "kind": "syntax_error",
                    "path": f.relative_to(repo_root).as_posix(),
                    "detail": str(e),
                    "severity": "P1",
                }
            )
            continue

        function_locs: list[int] = []
        class_methods: list[int] = []
        import_count = 0
        module = module_by_file[f]

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                end = getattr(node, "end_lineno", node.lineno)
                function_locs.append(max(1, end - node.lineno + 1))
            elif isinstance(node, ast.ClassDef):
                methods = sum(1 for body_node in node.body if isinstance(body_node, (ast.FunctionDef, ast.AsyncFunctionDef)))
                class_methods.append(methods)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                import_count += 1

        fan_out_targets: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    target = resolve_to_known_module(alias.name, known_modules)
                    if target:
                        fan_out_targets.add(target)
            elif isinstance(node, ast.ImportFrom):
                raw = resolve_relative_import(module, node.module, node.level)
                target = resolve_to_known_module(raw, known_modules)
                if target:
                    fan_out_targets.add(target)

        edges[module].update(t for t in fan_out_targets if t != module)

        rel_path = f.relative_to(repo_root).as_posix()
        layer = classify_layer(rel_path, layer_patterns)
        fm = FileMetrics(
            path=rel_path,
            module=module,
            layer=layer,
            file_loc=loc,
            max_function_loc=max(function_locs) if function_locs else 0,
            max_class_methods=max(class_methods) if class_methods else 0,
            import_count=import_count,
            max_nesting=max_nesting_depth(tree),
            fan_out=len(fan_out_targets),
        )
        metrics.append(fm)

    layer_by_module = {m.module: m.layer for m in metrics}

    for src, targets in edges.items():
        src_layer = layer_by_module.get(src, "unknown")
        allowed = set(allowed_dependencies.get(src_layer, []))
        for dst in targets:
            dst_layer = layer_by_module.get(dst, "unknown")
            if allowed and dst_layer not in allowed:
                violations.append(
                    {
                        "kind": "layering_violation",
                        "source_module": src,
                        "source_layer": src_layer,
                        "target_module": dst,
                        "target_layer": dst_layer,
                        "severity": "P1" if src_layer in {"domain", "service"} else "P2",
                    }
                )

    cycles = find_cycles(edges)
    for cyc in cycles:
        violations.append(
            {
                "kind": "import_cycle",
                "modules": cyc,
                "severity": "P1",
            }
        )

    metric_violations: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for fm in metrics:
        if fm.file_loc > limits["file_loc"]:
            metric_violations[fm.path].append({"metric": "file_loc", "actual": fm.file_loc, "threshold": limits["file_loc"]})
        if fm.max_function_loc > limits["function_loc"]:
            metric_violations[fm.path].append({"metric": "function_loc", "actual": fm.max_function_loc, "threshold": limits["function_loc"]})
        if fm.max_class_methods > limits["class_methods"]:
            metric_violations[fm.path].append({"metric": "class_methods", "actual": fm.max_class_methods, "threshold": limits["class_methods"]})
        if fm.import_count > limits["max_imports"]:
            metric_violations[fm.path].append({"metric": "max_imports", "actual": fm.import_count, "threshold": limits["max_imports"]})
        if fm.max_nesting > limits["nesting"]:
            metric_violations[fm.path].append({"metric": "nesting", "actual": fm.max_nesting, "threshold": limits["nesting"]})

    cycle_modules = {m for cyc in cycles for m in cyc}
    layer_violation_by_path: dict[str, list[dict[str, Any]]] = defaultdict(list)
    module_to_path = {m.module: m.path for m in metrics}
    for v in violations:
        if v["kind"] == "layering_violation":
            path = module_to_path.get(v["source_module"])
            if path:
                layer_violation_by_path[path].append(v)

    hotspots: list[dict[str, Any]] = []
    for idx, fm in enumerate(sorted(metrics, key=lambda x: x.path), start=1):
        path_violations = metric_violations.get(fm.path, [])
        layer_v = layer_violation_by_path.get(fm.path, [])
        in_cycle = fm.module in cycle_modules
        if not path_violations and not layer_v and not in_cycle:
            continue

        hints: list[str] = []
        for v in path_violations:
            if v["metric"] == "file_loc":
                hints.append("Split file by responsibility into submodules and keep public surface thin")
            elif v["metric"] == "function_loc":
                hints.append("Extract long functions into focused helpers/use-case units")
            elif v["metric"] == "class_methods":
                hints.append("Split class into collaborators with single responsibility")
            elif v["metric"] == "max_imports":
                hints.append("Reduce dependency fan-out via facade/port interfaces")
            elif v["metric"] == "nesting":
                hints.append("Flatten control flow using guard clauses and strategy helpers")
        if layer_v:
            hints.append("Restore dependency direction with port/interface boundaries between layers")
        if in_cycle:
            hints.append("Break import cycle by extracting shared contract module or inversion via protocol")

        sev = "P2"
        if in_cycle or layer_v:
            sev = "P1"
        if any(v["metric"] in {"file_loc", "function_loc"} and v["actual"] >= 2 * v["threshold"] for v in path_violations):
            sev = "P1"

        hotspots.append(
            {
                "hotspot_id": f"HS-{idx:03d}",
                "path": fm.path,
                "module": fm.module,
                "layer": fm.layer,
                "metrics": {
                    "file_loc": fm.file_loc,
                    "max_function_loc": fm.max_function_loc,
                    "max_class_methods": fm.max_class_methods,
                    "import_count": fm.import_count,
                    "max_nesting": fm.max_nesting,
                    "fan_out": fm.fan_out,
                },
                "threshold_breaches": path_violations,
                "layering_violations": layer_v,
                "cycle_involved": in_cycle,
                "refactor_hint": hints[0] if hints else "No hint",
                "severity": sev,
                "status": "open",
            }
        )

    hotspots.sort(key=lambda h: (h["severity"], -len(h["threshold_breaches"]), h["path"]))

    return {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "roots": [r.as_posix() for r in roots],
        "limits": limits,
        "python_files": len(metrics),
        "hotspots": hotspots,
        "violations": violations,
        "cycles": cycles,
    }


def write_markdown(result: dict[str, Any], out_md: Path) -> None:
    hotspots = result["hotspots"]
    violations = result["violations"]
    cycles = result["cycles"]
    limits = result["limits"]

    lines: list[str] = []
    lines.append("# DETM Runtime OOP Hotspots")
    lines.append("")
    lines.append(f"- Generated at: `{result['generated_at']}`")
    lines.append(f"- Roots: `{', '.join(result['roots'])}`")
    lines.append(f"- Python files scanned: `{result['python_files']}`")
    lines.append("")
    lines.append("## Policy Limits")
    lines.append("")
    lines.append("| Metric | Threshold |")
    lines.append("|---|---:|")
    lines.append(f"| file_loc | {limits['file_loc']} |")
    lines.append(f"| function_loc | {limits['function_loc']} |")
    lines.append(f"| class_methods | {limits['class_methods']} |")
    lines.append(f"| max_imports | {limits['max_imports']} |")
    lines.append(f"| nesting | {limits['nesting']} |")
    lines.append("")
    lines.append("## Hotspot Summary")
    lines.append("")
    lines.append(f"- Hotspots: `{len(hotspots)}`")
    lines.append(f"- Structural violations (layering + cycles + syntax): `{len(violations)}`")
    lines.append(f"- Import cycles: `{len(cycles)}`")
    lines.append("")
    lines.append("## Hotspot Table")
    lines.append("")
    lines.append("| id | path | layer | severity | breaches | cycle | refactor_hint |")
    lines.append("|---|---|---|---|---:|---|---|")
    for h in hotspots[:80]:
        lines.append(
            f"| `{h['hotspot_id']}` | `{h['path']}` | `{h['layer']}` | `{h['severity']}` | {len(h['threshold_breaches']) + len(h['layering_violations'])} | {'yes' if h['cycle_involved'] else 'no'} | {h['refactor_hint']} |"
        )

    if len(hotspots) > 80:
        lines.append("")
        lines.append(f"Truncated view: showing first 80 of {len(hotspots)} hotspots.")

    lines.append("")
    lines.append("## Import Cycles")
    lines.append("")
    if not cycles:
        lines.append("- No import cycles detected.")
    else:
        for idx, cyc in enumerate(cycles, start=1):
            lines.append(f"- Cycle {idx}: `{' -> '.join(cyc)}`")

    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Runtime OOP hotspot detector for DETM")
    parser.add_argument("--repo-root", default=".", help="Repository root")
    parser.add_argument("--roots", nargs="+", default=["detm", "detm_app"], help="Roots to scan")
    parser.add_argument("--policy", default="tools/oop_gatekeeper_policy.yaml", help="Policy YAML path")
    parser.add_argument("--out-json", default=None, help="Output JSON path")
    parser.add_argument("--out-md", default=None, help="Output markdown report path")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    roots = [Path(r).resolve() for r in args.roots]
    policy = read_policy(Path(args.policy).resolve())

    result = analyze(repo_root=repo_root, roots=roots, policy=policy)

    date_tag = dt.date.today().isoformat()
    out_json = Path(args.out_json) if args.out_json else Path(f"docs/rus/90_notes/runtime_oop_hotspots_{date_tag}.json")
    out_md = Path(args.out_md) if args.out_md else Path(f"docs/rus/90_notes/runtime_oop_hotspots_{date_tag}.md")

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    write_markdown(result, out_md)

    print(json.dumps({
        "python_files": result["python_files"],
        "hotspots": len(result["hotspots"]),
        "violations": len(result["violations"]),
        "cycles": len(result["cycles"]),
        "out_json": out_json.as_posix(),
        "out_md": out_md.as_posix(),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
