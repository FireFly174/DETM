"""Headless runner for DETM integration testing.

The runner loads a configuration, prepares a symbol alphabet, runs several
episodes and writes signatures/metrics to disk without any UI or scheduler
machinery. This serves as a predictable integration harness for downstream
systems.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, List

import numpy as np

from runtime import api
from runtime.config import DETMConfig
from runtime.influence import DETMInfluence
from runtime.schemas import get_schema_versions
from runtime.symbols import alphabet, make_symbol


def _load_config(path: Path | None) -> DETMConfig:
    if path is None:
        return DETMConfig()
    data = json.loads(path.read_text(encoding="utf-8"))
    return DETMConfig.from_dict(data)


def _influence_sequence(symbol_ids: List[str]) -> Iterable[DETMInfluence]:
    for sid in symbol_ids:
        yield make_symbol(sid)


def run_episode(config: DETMConfig, seed: int, influences: Iterable[DETMInfluence], steps: int):
    state = api.reset(config, seed)
    history = []
    for influence in influences:
        state, obs = api.step(state, influence, steps, None)
        history.append({
            "signature": obs.signature.as_dict(),
            "events": obs.events,
            "cost": obs.cost,
            "quality": obs.quality,
        })
    return state, history


def main() -> None:  # pragma: no cover - CLI utility
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=None, help="Path to DETM config (JSON)")
    parser.add_argument("--seeds", type=int, nargs="*", default=[1], help="Seeds to run")
    parser.add_argument("--steps", type=int, default=4, help="Ticks per influence")
    parser.add_argument("--symbols", type=str, nargs="*", default=None, help="Symbol IDs to apply")
    parser.add_argument("--out", type=Path, default=Path("runs/headless_runner"), help="Output directory")

    args = parser.parse_args()
    config = _load_config(args.config)
    symbols = args.symbols if args.symbols else list(symbol.symbol_id for symbol in alphabet())

    args.out.mkdir(parents=True, exist_ok=True)
    catalog = {"schema_versions": get_schema_versions(), "runs": []}

    for seed in args.seeds:
        influences = list(_influence_sequence(symbols))
        state, history = run_episode(config, seed, influences, steps=args.steps)
        blob = api.serialize(state)
        digest = api.digest(state)

        run_dir = args.out / f"seed_{seed:04d}"
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "history.jsonl").write_text("\n".join(json.dumps(entry) for entry in history), encoding="utf-8")
        (run_dir / "state.msgpack").write_bytes(blob)
        (run_dir / "digest.json").write_text(json.dumps(digest.as_dict(), indent=2), encoding="utf-8")

        catalog["runs"].append({"seed": seed, "digest": digest.as_dict(), "state_blob": str(run_dir / "state.msgpack")})

    catalog_path = args.out / "catalog.json"
    catalog_path.write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    print(f"[OK] {len(catalog['runs'])} run(s) complete. Catalog: {catalog_path.resolve()}")


if __name__ == "__main__":
    main()
