"""Configuration objects for DETM runtime APIs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict

from detm.core.entropy import DynamicsParameters
from detm.runtime.config.normalization import (
    level_fallback_chain as _level_fallback_chain,
    normalize_artifact_storage_policy as _normalize_artifact_storage_policy,
    normalize_pattern_reuse_scope as _normalize_pattern_reuse_scope,
)
from detm.runtime.level_policy import LevelPolicy
from detm.runtime.schemas import DETM_CONFIG_V1

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
    # "minimal" -> no CPU field copies; "cpu_full" -> allow CPU analyses (attractors, etc.)
    observables_mode: str = "minimal"
    # Trace-level boundary flux proxies (Φ_boundary(t) etc.). Off by default to avoid extra per-step work.
    trace_boundary_flux: bool = False
    watch_trace_enabled: bool = True
    trace_system_retention_window: int = 0
    trace_watch_retention_window: int = 0
    trace_watch_compaction_budget: int = 0
    artifact_storage_policy: Dict[str, Dict[str, Dict[str, int]]] = field(default_factory=dict)
    pattern_reuse_enabled: bool = True
    pattern_reuse_scope: str = "portable"  # global | portable | strict
    pattern_store_path: str | None = None
    pattern_cache_capacity: int = 128
    pattern_cache_ttl_steps: int = 4096
    pattern_prune_error_threshold: float = 0.05
    pattern_prune_deviation_threshold: float = 0.5
    level_policy: LevelPolicy = field(default_factory=LevelPolicy)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        dyn = data.pop("dynamics")
        data["dynamics"] = asdict(DynamicsParameters(**dyn))
        level_policy_raw = data.pop("level_policy", None)
        if isinstance(level_policy_raw, dict):
            data["level_policy"] = LevelPolicy.from_dict(level_policy_raw).to_dict()
        else:
            data["level_policy"] = self.level_policy.to_dict()
        data["artifact_storage_policy"] = _normalize_artifact_storage_policy(data.get("artifact_storage_policy", {}))
        data["pattern_reuse_scope"] = _normalize_pattern_reuse_scope(data.get("pattern_reuse_scope", "portable"))
        return data

    def resolve_artifact_storage_policy(self, *, artifact: str, level: str = "L0") -> Dict[str, int]:
        artifact_name = str(artifact).strip()
        level_name = str(level).strip() or "L0"
        policy = _normalize_artifact_storage_policy(self.artifact_storage_policy)

        def _lookup(level_key: str, artifact_key: str) -> Dict[str, int] | None:
            level_rules = policy.get(level_key)
            if not isinstance(level_rules, dict):
                return None
            for key in (artifact_key, "default", "*"):
                if key in level_rules:
                    rule = level_rules.get(key, {})
                    return {
                        "retention_window": max(0, int(dict(rule).get("retention_window", 0))),
                        "compaction_budget": max(0, int(dict(rule).get("compaction_budget", 0))),
                    }
            return None

        for level_key in [*_level_fallback_chain(level_name), "default", "*"]:
            rule = _lookup(level_key, artifact_name)
            if rule is not None:
                return rule

        if artifact_name == "trace":
            return {
                "retention_window": max(0, int(self.trace_system_retention_window)),
                "compaction_budget": 0,
            }
        if artifact_name in {"watch_trace", "watch_contract", "outerfields", "operator_decisions"}:
            return {
                "retention_window": max(0, int(self.trace_watch_retention_window)),
                "compaction_budget": max(0, int(self.trace_watch_compaction_budget)),
            }
        return {"retention_window": 0, "compaction_budget": 0}

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "DETMConfig":
        data = dict(payload)
        version = data.get("config_version", DETM_CONFIG_V1)
        dynamics_raw = data.get("dynamics", {})
        dynamics = DynamicsParameters(**dynamics_raw) if isinstance(dynamics_raw, dict) else dynamics_raw
        level_policy_raw = data.get("level_policy")
        if isinstance(level_policy_raw, LevelPolicy):
            level_policy = level_policy_raw
        elif isinstance(level_policy_raw, dict):
            level_policy = LevelPolicy.from_dict(level_policy_raw)
        else:
            level_policy = LevelPolicy()
        return cls(
            config_version=version,
            backend=str(data.get("backend", "torch")),
            device=str(data.get("device", "cuda")),
            width=int(data.get("width", 24)),
            height=int(data.get("height", 24)),
            boundary=str(data.get("boundary", "periodic")),
            dynamics=dynamics,
            initial_noise=float(data.get("initial_noise", 0.08)),
            observables_mode=str(data.get("observables_mode", "minimal")),
            trace_boundary_flux=bool(data.get("trace_boundary_flux", False)),
            watch_trace_enabled=bool(data.get("watch_trace_enabled", True)),
            trace_system_retention_window=max(0, int(data.get("trace_system_retention_window", 0))),
            trace_watch_retention_window=max(0, int(data.get("trace_watch_retention_window", 0))),
            trace_watch_compaction_budget=max(0, int(data.get("trace_watch_compaction_budget", 0))),
            artifact_storage_policy=_normalize_artifact_storage_policy(data.get("artifact_storage_policy", {})),
            pattern_reuse_enabled=bool(data.get("pattern_reuse_enabled", True)),
            pattern_reuse_scope=_normalize_pattern_reuse_scope(data.get("pattern_reuse_scope", "portable")),
            pattern_store_path=None
            if data.get("pattern_store_path") in (None, "")
            else str(data.get("pattern_store_path")),
            pattern_cache_capacity=max(1, int(data.get("pattern_cache_capacity", 128))),
            pattern_cache_ttl_steps=max(1, int(data.get("pattern_cache_ttl_steps", 4096))),
            pattern_prune_error_threshold=float(data.get("pattern_prune_error_threshold", 0.05)),
            pattern_prune_deviation_threshold=float(data.get("pattern_prune_deviation_threshold", 0.5)),
            level_policy=level_policy,
        )


__all__ = ["DETMConfig"]
