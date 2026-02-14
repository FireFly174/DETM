"""Pattern memory record contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class PatternRecord:
    key: str
    blend: float
    error: float
    deviation: float
    hits: int = 1
    updated_step: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": str(self.key),
            "blend": float(self.blend),
            "error": float(self.error),
            "deviation": float(self.deviation),
            "hits": int(self.hits),
            "updated_step": int(self.updated_step),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "PatternRecord":
        data = dict(payload)
        return cls(
            key=str(data.get("key", "")),
            blend=float(data.get("blend", 0.0)),
            error=float(data.get("error", 0.0)),
            deviation=float(data.get("deviation", 0.0)),
            hits=max(1, int(data.get("hits", 1))),
            updated_step=max(0, int(data.get("updated_step", 0))),
        )


__all__ = ["PatternRecord"]
