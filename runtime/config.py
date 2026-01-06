"""Configuration objects for DETM runtime APIs."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict

from core.entropy import DynamicsParameters
from runtime.schemas import DETM_CONFIG_V1


@dataclass(frozen=True)
class DETMConfig:
    """Structured configuration with explicit versioning.

    The configuration schema is intentionally small and focused on the minimal
    parameters required to run the L0 dynamics. Additional fields can be added
    in backward-compatible fashion by bumping the minor version.
    """

    config_version: str = DETM_CONFIG_V1
    backend: str = "torch"  # "numpy" | "torch"
    device: str = "cuda"  # preferred device; may fall back to cpu if unavailable
    width: int = 24
    height: int = 24
    boundary: str = "periodic"
    dynamics: DynamicsParameters = DynamicsParameters()
    initial_noise: float = 0.08

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        dyn = data.pop("dynamics")
        data["dynamics"] = asdict(DynamicsParameters(**dyn))
        return data

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "DETMConfig":
        data = dict(payload)
        version = data.get("config_version", DETM_CONFIG_V1)
        dynamics_raw = data.get("dynamics", {})
        dynamics = DynamicsParameters(**dynamics_raw) if isinstance(dynamics_raw, dict) else dynamics_raw
        return cls(
            config_version=version,
            backend=str(data.get("backend", "torch")),
            device=str(data.get("device", "cuda")),
            width=int(data.get("width", 24)),
            height=int(data.get("height", 24)),
            boundary=str(data.get("boundary", "periodic")),
            dynamics=dynamics,
            initial_noise=float(data.get("initial_noise", 0.08)),
        )


__all__ = ["DETMConfig"]
