"""Symbol library for DETM influences."""

from __future__ import annotations

from typing import Dict, Iterable, List

from runtime.influence import DETMInfluence


_SYMBOL_TEMPLATES: Dict[str, dict] = {
    "pulse": {"amplitude": 0.15, "region": None},
    "ring": {"amplitude": 0.1, "region": (0, 0, 0)},
    "stripe": {"amplitude": 0.08},
    "noise_burst": {"amplitude": 0.2},
    "cooldown": {"amplitude": -0.1},
    "focus": {"amplitude": 0.05},
    "disturb": {"amplitude": 0.12},
    "seeded": {"amplitude": 0.1, "seed": 123},
    "phase_shift": {"amplitude": 0.07, "phase": 0.5},
    "sustain": {"amplitude": 0.02, "duration": 4},
}


def make_symbol(symbol_id: str, **params) -> DETMInfluence:
    base = dict(_SYMBOL_TEMPLATES.get(symbol_id, {}))
    base.update(params)
    return DETMInfluence(symbol_id=symbol_id, **base)


def list_symbols() -> List[str]:
    return sorted(_SYMBOL_TEMPLATES.keys())


def alphabet() -> Iterable[DETMInfluence]:
    for symbol_id in list_symbols():
        yield make_symbol(symbol_id)


__all__ = ["alphabet", "list_symbols", "make_symbol"]
