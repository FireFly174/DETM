"""Configuration objects for DETM runtime APIs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict
from urllib.parse import urlsplit, urlunsplit

from detm.core.entropy import DynamicsParameters
from detm.runtime.config.normalization import (
    level_fallback_chain as _level_fallback_chain,
    normalize_artifact_storage_policy as _normalize_artifact_storage_policy,
    normalize_pattern_reuse_scope as _normalize_pattern_reuse_scope,
)
from detm.runtime.level_policy import LevelPolicy
from detm.runtime.schemas import DETM_CONFIG_V1


def _normalize_shape(raw_shape: Any, *, width: Any, height: Any) -> tuple[int, ...]:
    if raw_shape in (None, "", (), []):
        dims = (int(height), int(width))
    else:
        dims = tuple(int(value) for value in raw_shape)
    if len(dims) < 2:
        raise ValueError("shape must contain at least two axes")
    if any(int(value) <= 0 for value in dims):
        raise ValueError("shape axes must be positive")
    return tuple(int(value) for value in dims)


def _normalize_multiscale_mode(raw: Any) -> str:
    value = str(raw or "observe").strip().lower()
    if value in {"observe", "hint", "jump"}:
        return value
    return "observe"


def _normalize_horizons(raw: Any) -> tuple[int, ...]:
    if raw in (None, "", (), []):
        return (1,)
    if isinstance(raw, (int, float)):
        values = [int(raw)]
    else:
        values = [int(value) for value in list(raw)]
    normalized = tuple(sorted({max(1, int(value)) for value in values}))
    return normalized if normalized else (1,)


def _safe_endpoint(raw: Any) -> str | None:
    if raw in (None, ""):
        return None
    value = str(raw).strip()
    if value == "":
        return None
    try:
        parsed = urlsplit(value)
    except Exception:
        return value
    if parsed.scheme == "" or parsed.netloc == "":
        return value
    hostname = parsed.hostname or ""
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    netloc = hostname
    if parsed.port is not None:
        netloc = f"{netloc}:{int(parsed.port)}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, "", ""))


@dataclass(frozen=True)
class MultiscaleCatalogConfig:
    enabled: bool = False
    mode: str = "observe"
    redis_url: str | None = None
    window_ticks: int = 10
    patch_radius: int = 1
    horizons: tuple[int, ...] = (1,)
    quantization: float = 0.05
    candidate_min_support: int = 3
    candidate_min_confidence: float = 0.75
    jump_max_error: float = 0.05
    commit_only_sampling: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "enabled", bool(self.enabled))
        object.__setattr__(self, "mode", _normalize_multiscale_mode(self.mode))
        object.__setattr__(
            self,
            "redis_url",
            None if self.redis_url in (None, "") else str(self.redis_url),
        )
        object.__setattr__(self, "window_ticks", max(1, int(self.window_ticks)))
        object.__setattr__(self, "patch_radius", max(0, int(self.patch_radius)))
        object.__setattr__(self, "horizons", _normalize_horizons(self.horizons))
        object.__setattr__(self, "quantization", max(1e-9, float(self.quantization)))
        object.__setattr__(self, "candidate_min_support", max(1, int(self.candidate_min_support)))
        object.__setattr__(
            self,
            "candidate_min_confidence",
            min(1.0, max(0.0, float(self.candidate_min_confidence))),
        )
        object.__setattr__(self, "jump_max_error", max(0.0, float(self.jump_max_error)))
        object.__setattr__(self, "commit_only_sampling", bool(self.commit_only_sampling))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": bool(self.enabled),
            "mode": str(self.mode),
            "redis_url": _safe_endpoint(self.redis_url),
            "window_ticks": int(self.window_ticks),
            "patch_radius": int(self.patch_radius),
            "horizons": list(self.horizons),
            "quantization": float(self.quantization),
            "candidate_min_support": int(self.candidate_min_support),
            "candidate_min_confidence": float(self.candidate_min_confidence),
            "jump_max_error": float(self.jump_max_error),
            "commit_only_sampling": bool(self.commit_only_sampling),
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any] | None) -> "MultiscaleCatalogConfig":
        data = {} if payload is None else dict(payload)
        return cls(
            enabled=bool(data.get("enabled", False)),
            mode=_normalize_multiscale_mode(data.get("mode", "observe")),
            redis_url=None if data.get("redis_url") in (None, "") else str(data.get("redis_url")),
            window_ticks=max(1, int(data.get("window_ticks", 10))),
            patch_radius=max(0, int(data.get("patch_radius", 1))),
            horizons=_normalize_horizons(data.get("horizons", (1,))),
            quantization=max(1e-9, float(data.get("quantization", 0.05))),
            candidate_min_support=max(1, int(data.get("candidate_min_support", 3))),
            candidate_min_confidence=min(1.0, max(0.0, float(data.get("candidate_min_confidence", 0.75)))),
            jump_max_error=max(0.0, float(data.get("jump_max_error", 0.05))),
            commit_only_sampling=bool(data.get("commit_only_sampling", True)),
        )


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
    shape: tuple[int, ...] = field(default_factory=tuple)
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
    multiscale_catalog: MultiscaleCatalogConfig = field(default_factory=MultiscaleCatalogConfig)
    level_policy: LevelPolicy = field(default_factory=LevelPolicy)

    def __post_init__(self) -> None:
        shape = _normalize_shape(self.shape, width=self.width, height=self.height)
        object.__setattr__(self, "shape", shape)
        object.__setattr__(self, "height", int(shape[-2]))
        object.__setattr__(self, "width", int(shape[-1]))
        multiscale_raw = self.multiscale_catalog
        if isinstance(multiscale_raw, MultiscaleCatalogConfig):
            multiscale_catalog = multiscale_raw
        elif isinstance(multiscale_raw, dict):
            multiscale_catalog = MultiscaleCatalogConfig.from_dict(multiscale_raw)
        else:
            multiscale_catalog = MultiscaleCatalogConfig()
        object.__setattr__(self, "multiscale_catalog", multiscale_catalog)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["shape"] = list(self.shape)
        data["height"] = int(self.height)
        data["width"] = int(self.width)
        dyn = data.pop("dynamics")
        data["dynamics"] = asdict(DynamicsParameters(**dyn))
        level_policy_raw = data.pop("level_policy", None)
        if isinstance(level_policy_raw, dict):
            data["level_policy"] = LevelPolicy.from_dict(level_policy_raw).to_dict()
        else:
            data["level_policy"] = self.level_policy.to_dict()
        data["artifact_storage_policy"] = _normalize_artifact_storage_policy(data.get("artifact_storage_policy", {}))
        data["pattern_reuse_scope"] = _normalize_pattern_reuse_scope(data.get("pattern_reuse_scope", "portable"))
        multiscale_raw = data.pop("multiscale_catalog", None)
        if isinstance(multiscale_raw, dict):
            data["multiscale_catalog"] = MultiscaleCatalogConfig.from_dict(multiscale_raw).to_dict()
        else:
            data["multiscale_catalog"] = self.multiscale_catalog.to_dict()
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
        multiscale_raw = data.get("multiscale_catalog")
        if isinstance(multiscale_raw, MultiscaleCatalogConfig):
            multiscale_catalog = multiscale_raw
        elif isinstance(multiscale_raw, dict):
            multiscale_catalog = MultiscaleCatalogConfig.from_dict(multiscale_raw)
        else:
            multiscale_catalog = MultiscaleCatalogConfig()
        return cls(
            config_version=version,
            backend=str(data.get("backend", "torch")),
            device=str(data.get("device", "cuda")),
            width=int(data.get("width", 24)),
            height=int(data.get("height", 24)),
            shape=_normalize_shape(data.get("shape"), width=data.get("width", 24), height=data.get("height", 24)),
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
            multiscale_catalog=multiscale_catalog,
            level_policy=level_policy,
        )

__all__ = ["DETMConfig", "MultiscaleCatalogConfig"]
