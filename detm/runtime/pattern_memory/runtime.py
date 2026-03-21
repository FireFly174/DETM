"""Pattern memory runtime orchestration."""

from __future__ import annotations

import hashlib
from collections import Counter, deque
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

import numpy as np

from detm.runtime.pattern_memory.cache import PatternCache
from detm.runtime.pattern_memory.flow import (
    compute_pattern_key as _compute_pattern_key_flow,
    extract_patch as _extract_patch_flow,
    is_reusable_record as _is_reusable_record_flow,
    lookup_candidates as _lookup_candidates_flow,
    normalize_context_token as _normalize_context_token_flow,
    remember_key as _remember_key_flow,
    runtime_key_from_config as _runtime_key_from_config_flow,
    scoped_key as _scoped_key_flow,
)
from detm.runtime.pattern_memory.record import BridgeRecord, BridgeRecordSource, PatternRecord, TrajectoryBody, VerificationRun
from detm.runtime.pattern_memory.scope import normalize_reuse_scope
from detm.runtime.pattern_memory.store import (
    FileBridgeSourceStore,
    FilePatternStore,
    FileTrajectoryBodyStore,
    FileVerificationRunStore,
)


def _quantize_array(array: np.ndarray, *, quantization: float) -> np.ndarray:
    scale = max(float(quantization), 1e-9)
    return np.round(np.asarray(array, dtype=float) / scale) * scale


def _hash_descriptor(*parts: object) -> str:
    digest = hashlib.sha1()
    for part in parts:
        if isinstance(part, np.ndarray):
            digest.update(np.ascontiguousarray(part).tobytes())
        else:
            digest.update(str(part).encode("utf-8"))
            digest.update(b"|")
    return digest.hexdigest()


def _safe_endpoint(raw: object) -> str | None:
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


def _bridge_source_store_path(path: Path) -> Path:
    stem = path.stem or path.name
    suffix = path.suffix or ".json"
    return path.with_name(f"{stem}.bridge_sources{suffix}")


def _bridge_verification_store_path(path: Path) -> Path:
    stem = path.stem or path.name
    suffix = path.suffix or ".json"
    return path.with_name(f"{stem}.bridge_verification_runs{suffix}")


def _trajectory_body_store_path(path: Path) -> Path:
    stem = path.stem or path.name
    suffix = path.suffix or ".json"
    return path.with_name(f"{stem}.trajectory_bodies{suffix}")


class PatternMemoryRuntime:
    def __init__(
        self,
        *,
        reuse_enabled: bool,
        cache_capacity: int,
        cache_ttl_steps: int,
        prune_error_threshold: float,
        prune_deviation_threshold: float,
        reuse_scope: str,
        store_path: str | None,
        multiscale_enabled: bool,
        multiscale_mode: str,
        multiscale_redis_url: str | None,
        multiscale_window_ticks: int,
        multiscale_patch_radius: int,
        multiscale_horizons: tuple[int, ...],
        multiscale_quantization: float,
        multiscale_candidate_min_support: int,
        multiscale_candidate_min_confidence: float,
        multiscale_jump_max_error: float,
        multiscale_commit_only_sampling: bool,
    ) -> None:
        self.reuse_enabled = bool(reuse_enabled)
        self.reuse_scope = normalize_reuse_scope(reuse_scope)
        self.prune_error_threshold = float(prune_error_threshold)
        self.prune_deviation_threshold = float(prune_deviation_threshold)
        self.cache = PatternCache(capacity=max(1, int(cache_capacity)), ttl_steps=max(1, int(cache_ttl_steps)))
        self.store = (
            None
            if store_path is None or not str(store_path).strip()
            else FilePatternStore(Path(str(store_path).strip()))
        )
        self.bridge_source_store = None
        self.trajectory_body_store = None
        self.verification_run_store = None
        if self.store is not None:
            self.bridge_source_store = FileBridgeSourceStore(_bridge_source_store_path(self.store.path))
            self.trajectory_body_store = FileTrajectoryBodyStore(_trajectory_body_store_path(self.store.path))
            self.verification_run_store = FileVerificationRunStore(_bridge_verification_store_path(self.store.path))
        if self.store is not None:
            for record in self.store.load().values():
                self.cache.put(record)
        self.multiscale_enabled = bool(multiscale_enabled)
        self.multiscale_mode = str(multiscale_mode or "observe")
        self.multiscale_redis_url = None if multiscale_redis_url in (None, "") else str(multiscale_redis_url)
        self.multiscale_window_ticks = max(1, int(multiscale_window_ticks))
        self.multiscale_patch_radius = max(0, int(multiscale_patch_radius))
        self.multiscale_horizons = tuple(sorted({max(1, int(value)) for value in tuple(multiscale_horizons)})) or (1,)
        self.multiscale_quantization = max(1e-9, float(multiscale_quantization))
        self.multiscale_candidate_min_support = max(1, int(multiscale_candidate_min_support))
        self.multiscale_candidate_min_confidence = min(1.0, max(0.0, float(multiscale_candidate_min_confidence)))
        self.multiscale_jump_max_error = max(0.0, float(multiscale_jump_max_error))
        self.multiscale_commit_only_sampling = bool(multiscale_commit_only_sampling)
        self._multiscale_snapshots: deque[dict[str, Any]] = deque(maxlen=self.multiscale_window_ticks)
        self._bridge_records: dict[str, BridgeRecord] = {}
        self._bridge_sources: dict[str, BridgeRecordSource] = (
            {} if self.bridge_source_store is None else self.bridge_source_store.load()
        )
        self._trajectory_bodies: dict[str, TrajectoryBody] = (
            {} if self.trajectory_body_store is None else self.trajectory_body_store.load()
        )
        self._verification_runs: dict[str, VerificationRun] = (
            {} if self.verification_run_store is None else self.verification_run_store.load()
        )
        self._verification_run_namespace = uuid4().hex
        self._transition_counts: dict[tuple[str, str], int] = {}
        self._multiscale_last_positions: dict[tuple[int, int], tuple[str, str]] = {}
        self._multiscale_last_tick: int = 0
        self._multiscale_backend_kind = "local"
        self._multiscale_backend_available = True
        if self.multiscale_redis_url is not None:
            self._multiscale_backend_kind = "redis"
            try:
                import redis as _redis  # type: ignore  # noqa: F401

                self._multiscale_backend_available = True
            except ModuleNotFoundError:
                self._multiscale_backend_available = False

    def make_key(self, *, energy: np.ndarray, center_x: int, center_y: int, radius: int, boundary: str) -> str:
        return _compute_pattern_key_flow(
            energy=energy,
            center_x=int(center_x),
            center_y=int(center_y),
            radius=int(radius),
            boundary=str(boundary),
        )

    def lookup(self, *, key: str, step_count: int) -> PatternRecord | None:
        return self.lookup_with_scope(
            key=key,
            step_count=step_count,
            level="L0",
            mode="minimal",
        )

    def lookup_with_scope(
        self,
        *,
        key: str,
        step_count: int,
        level: str,
        mode: str,
    ) -> PatternRecord | None:
        base_key = str(key)
        candidates = self._lookup_candidates(base_key=base_key, level=str(level), mode=str(mode))
        loaded_map: dict[str, PatternRecord] | None = None
        for candidate in candidates:
            record = self.cache.get(candidate, step_count=int(step_count))
            if record is not None and self._is_reusable_record(record):
                return record
            if record is not None:
                self.prune()
                continue
            if self.store is None:
                continue
            if loaded_map is None:
                loaded_map = self.store.load()
            loaded = loaded_map.get(candidate)
            if loaded is None:
                continue
            if not self._is_reusable_record(loaded):
                self.prune()
                continue
            self.cache.put(loaded)
            return loaded
        return None

    def remember(
        self,
        *,
        key: str,
        blend: float,
        error: float,
        deviation: float,
        step_count: int,
        base_hits: int = 0,
        level: str = "L0",
        mode: str = "minimal",
    ) -> PatternRecord:
        remembered_key = self._remember_key(base_key=str(key), level=str(level), mode=str(mode))
        record = PatternRecord(
            key=remembered_key,
            blend=float(blend),
            error=float(error),
            deviation=float(deviation),
            hits=max(1, int(base_hits) + 1),
            updated_step=max(0, int(step_count)),
        )
        self.cache.put(record)
        if self.store is not None:
            self.store.upsert(record)
        self.prune()
        return record

    def prune(self) -> int:
        removed = self.cache.prune(
            error_threshold=float(self.prune_error_threshold),
            deviation_threshold=float(self.prune_deviation_threshold),
        )
        if self.store is not None:
            removed += self.store.prune(
                error_threshold=float(self.prune_error_threshold),
                deviation_threshold=float(self.prune_deviation_threshold),
            )
        return int(removed)

    def cache_size(self) -> int:
        return int(len(self.cache))

    def multiscale_snapshot_count(self) -> int:
        return int(len(self._multiscale_snapshots))

    def bridge_source_count(self) -> int:
        return int(len(self._bridge_sources))

    def verification_run_count(self) -> int:
        return int(len(self._verification_runs))

    def multiscale_backend_info(self) -> dict[str, Any]:
        return {
            "kind": str(self._multiscale_backend_kind),
            "available": bool(self._multiscale_backend_available),
            "endpoint": _safe_endpoint(self.multiscale_redis_url),
        }

    def observe_multiscale(
        self,
        *,
        energy: np.ndarray,
        tick: int,
        boundary: str,
        level: str,
        trace_ref: str,
    ) -> dict[str, Any]:
        if not bool(self.multiscale_enabled):
            return {
                "mode": str(self.multiscale_mode),
                "catalog_backend": self.multiscale_backend_info(),
                "candidates": [],
                "sources": [],
                "bodies": [],
                "summary": {
                    "coarsen_candidate_count": 0,
                    "refine_candidate_count": 0,
                    "attractor_candidate_count": 0,
                    "window_count": 0,
                    "unique_window_signature_count": 0,
                },
                "hit_count": 0,
                "miss_count": 0,
                "record_count": int(len(self._bridge_records)),
                "source_count": int(len(self._bridge_sources)),
                "body_count": int(len(self._trajectory_bodies)),
                "verification_run_count": int(len(self._verification_runs)),
            }

        projected = np.asarray(energy, dtype=float)
        quantized_energy = _quantize_array(projected, quantization=self.multiscale_quantization)
        windows: list[dict[str, Any]] = []
        signature_counts: Counter[str] = Counter()
        candidate_rows: list[dict[str, Any]] = []
        source_rows_by_id: dict[str, dict[str, Any]] = {}
        verification_rows: list[dict[str, Any]] = []
        repeated_hits = 0
        refine_candidates = 0
        candidate_threshold = max(1, int(self.multiscale_candidate_min_support))
        h, w = int(quantized_energy.shape[0]), int(quantized_energy.shape[1])

        for center_y in range(h):
            for center_x in range(w):
                patch = self._extract_patch(
                    quantized_energy,
                    center_x=center_x,
                    center_y=center_y,
                    radius=int(self.multiscale_patch_radius),
                    boundary=str(boundary),
                )
                interface_radius = int(self.multiscale_patch_radius) + 1
                interface_patch = self._extract_patch(
                    quantized_energy,
                    center_x=center_x,
                    center_y=center_y,
                    radius=interface_radius,
                    boundary=str(boundary),
                )
                interface_descriptor = self._interface_descriptor(interface_patch)
                window_signature = _hash_descriptor("window", patch, f"r={self.multiscale_patch_radius}", boundary)
                interface_signature = _hash_descriptor("interface", interface_descriptor, f"r={interface_radius}", boundary)
                signature_counts[window_signature] += 1
                windows.append(
                    {
                        "center": [int(center_y), int(center_x)],
                        "window_signature": window_signature,
                        "interface_signature": interface_signature,
                        "patch_shape": [int(value) for value in patch.shape],
                        "interface_radius": int(interface_radius),
                        "patch_mean": float(np.mean(patch)),
                        "patch_var": float(np.var(patch)),
                        "boundary_activity": float(np.max(interface_descriptor) - np.min(interface_descriptor)),
                    }
                )

        previous_positions = dict(self._multiscale_last_positions)
        previous_records = dict(self._bridge_records)
        previous_sources = dict(self._bridge_sources)
        next_trajectory_bodies = dict(self._trajectory_bodies)
        next_verification_runs = dict(self._verification_runs)
        current_positions: dict[tuple[int, int], tuple[str, str]] = {}
        next_records = dict(previous_records)
        next_sources = dict(previous_sources)
        body_rows_by_id: dict[str, dict[str, Any]] = {}
        for window in windows:
            center_y, center_x = int(window["center"][0]), int(window["center"][1])
            position = (center_y, center_x)
            window_signature = str(window["window_signature"])
            interface_signature = str(window["interface_signature"])
            current_positions[position] = (window_signature, interface_signature)
            record_id = f"op:{str(level)}:{window_signature}:{interface_signature}:{int(self.multiscale_horizons[0])}"
            previous = previous_records.get(record_id)
            support = 1 if previous is None else int(previous.support) + 1
            usage_count = 0 if previous is None else int(previous.usage_count)
            if previous is not None:
                repeated_hits += 1
                usage_count += 1
            confidence = min(1.0, float(support) / float(candidate_threshold))
            result_signature = window_signature
            prev_pair = previous_positions.get(position)
            if prev_pair is not None:
                result_signature = str(window_signature)
                self._transition_counts[(str(prev_pair[0]), str(window_signature))] = (
                    int(self._transition_counts.get((str(prev_pair[0]), str(window_signature)), 0)) + 1
                )
                if str(prev_pair[0]) != str(window_signature):
                    refine_candidates += 1
            source_id: str | None = None
            source = None
            if int(support) >= candidate_threshold and confidence >= float(self.multiscale_candidate_min_confidence):
                source_id = f"source:{str(level)}:{window_signature}:{interface_signature}:{int(self.multiscale_horizons[0])}"
                previous_source = previous_sources.get(source_id)
                source_status = "candidate_ready"
                if previous_source is not None and str(previous_source.status):
                    source_status = str(previous_source.status)
                previous_verification = (
                    {} if previous_source is None else dict(previous_source.verification_summary)
                )
                verification_count = max(0, int(previous_verification.get("verification_count", 0)))
                success_count = max(0, int(previous_verification.get("success_count", 0)))
                failure_count = max(0, int(previous_verification.get("failure_count", 0)))
                last_status = "observed"
                matched = None
                if previous_source is not None:
                    verification_count += 1
                    matched = bool(str(previous_source.result_signature) == str(result_signature))
                    if matched:
                        success_count += 1
                        last_status = "matched"
                    else:
                        failure_count += 1
                        last_status = "mismatch"
                validity_envelope = {
                    "boundary": str(boundary),
                    "patch_radius": int(self.multiscale_patch_radius),
                    "interface_radius": int(window["interface_radius"]),
                    "quantization": float(self.multiscale_quantization),
                    "jump_max_error": float(self.multiscale_jump_max_error),
                }
                forward_body_id = f"body:forward:{str(source_id)}"
                reverse_body_id = f"body:reverse:{str(source_id)}"
                forward_body = {
                    "type": "forward_body_observe_placeholder",
                    "result_signature": result_signature,
                    "patch_mean": float(window["patch_mean"]),
                    "patch_var": float(window["patch_var"]),
                    "boundary_activity": float(window["boundary_activity"]),
                }
                reverse_body = {
                    "type": "reverse_refine_placeholder",
                    "mode": "canonical_reconstruction_placeholder",
                    "available": False,
                }
                source = BridgeRecordSource(
                    source_id=source_id,
                    level_src=str(level),
                    level_dst=f"{str(level)}+1",
                    window_signature=window_signature,
                    interface_signature=interface_signature,
                    horizon_k=int(self.multiscale_horizons[0]),
                    result_signature=result_signature,
                    window_geometry={
                        "patch_radius": int(self.multiscale_patch_radius),
                        "interface_radius": int(window["interface_radius"]),
                        "patch_shape": list(window["patch_shape"]),
                    },
                    invariants_preserved=(
                        "window_signature",
                        "interface_signature",
                        "boundary",
                        "quantization",
                    ),
                    forward_body=forward_body,
                    reverse_body=reverse_body,
                    validity_envelope=validity_envelope,
                    verification_summary={
                        "support": int(support),
                        "confidence": float(confidence),
                        "usage_count": int(usage_count),
                        "verification_count": int(verification_count),
                        "success_count": int(success_count),
                        "failure_count": int(failure_count),
                        "last_status": str(last_status),
                        "last_verified_tick": int(tick),
                    },
                    provenance={
                        "mode": str(self.multiscale_mode),
                        "backend": dict(self.multiscale_backend_info()),
                        "trace_ref": str(trace_ref),
                        "first_observed_tick": int(tick if previous_source is None else previous_source.provenance.get("first_observed_tick", tick)),
                    },
                    status=source_status,
                    db_refs={
                        "source_store": "bridge_record_sources",
                        "trajectory_body_store": "trajectory_bodies",
                        "forward_body_id": str(forward_body_id),
                        "reverse_body_id": str(reverse_body_id),
                    },
                )
                next_sources[source_id] = source
                for body_record in (
                    TrajectoryBody(
                        body_id=str(forward_body_id),
                        source_id=str(source_id),
                        body_role="forward",
                        level_src=str(level),
                        level_dst=f"{str(level)}+1",
                        horizon_k=int(self.multiscale_horizons[0]),
                        body=forward_body,
                        provenance={
                            "trace_ref": str(trace_ref),
                            "tick": int(tick),
                            "mode": str(self.multiscale_mode),
                        },
                    ),
                    TrajectoryBody(
                        body_id=str(reverse_body_id),
                        source_id=str(source_id),
                        body_role="reverse",
                        level_src=str(level),
                        level_dst=f"{str(level)}+1",
                        horizon_k=int(self.multiscale_horizons[0]),
                        body=reverse_body,
                        provenance={
                            "trace_ref": str(trace_ref),
                            "tick": int(tick),
                            "mode": str(self.multiscale_mode),
                        },
                    ),
                ):
                    next_trajectory_bodies[str(body_record.body_id)] = body_record
                    body_rows_by_id[str(body_record.body_id)] = body_record.to_dict()
                verification_rows.append(
                    {
                        "verification_id": (
                            f"verify:{self._verification_run_namespace}:{str(source_id)}:"
                            f"{int(tick)}:{int(center_y)}:{int(center_x)}"
                        ),
                        "schema_version": "verification_run/v1",
                        "source_id": str(source_id),
                        "tick": int(tick),
                        "trace_ref": str(trace_ref),
                        "level": str(level),
                        "window_signature": window_signature,
                        "interface_signature": interface_signature,
                        "result_signature": result_signature,
                        "matched": matched,
                        "status": str(last_status),
                        "confidence": float(confidence),
                        "support": int(support),
                        "usage_count": int(usage_count),
                        "details": {
                            "verification_count": int(verification_count),
                            "success_count": int(success_count),
                            "failure_count": int(failure_count),
                            "center": [int(center_y), int(center_x)],
                        },
                    }
                )
            bridge = BridgeRecord(
                record_id=record_id,
                level=str(level),
                window_signature=window_signature,
                interface_signature=interface_signature,
                horizon_k=int(self.multiscale_horizons[0]),
                result_signature=result_signature,
                error_bound=0.0,
                confidence=confidence,
                usage_count=usage_count,
                support=support,
                first_seen_tick=int(tick if previous is None else previous.first_seen_tick),
                last_seen_tick=int(tick),
                forward_descriptor={
                    "type": "forward_compress",
                    "mode": str(self.multiscale_mode),
                    "result_signature": result_signature,
                    "horizon_k": int(self.multiscale_horizons[0]),
                },
                reverse_descriptor_short={
                    "type": "reverse_refine",
                    "mode": "canonical_reconstruction_placeholder",
                    "available": False,
                },
                validity_envelope={
                    "boundary": str(boundary),
                    "patch_radius": int(self.multiscale_patch_radius),
                    "quantization": float(self.multiscale_quantization),
                    "jump_max_error": float(self.multiscale_jump_max_error),
                },
                verification_stats={
                    "support": int(support),
                    "transition_out_degree": int(
                        sum(1 for (source, _target) in self._transition_counts.keys() if source == window_signature)
                    ),
                    "last_verified_tick": int(tick),
                },
                db_refs={
                    "source_id": source_id,
                    "forward": None if source_id is None else f"body:forward:{str(source_id)}",
                    "reverse": None if source_id is None else f"body:reverse:{str(source_id)}",
                },
            )
            next_records[record_id] = bridge
            if source_id is not None:
                candidate_rows.append(
                    {
                        "record_id": str(record_id),
                        "source_id": str(source_id),
                        "level": str(level),
                        "center": [int(center_y), int(center_x)],
                        "window_signature": window_signature,
                        "interface_signature": interface_signature,
                        "support": int(support),
                        "confidence": float(confidence),
                        "candidate_type": "coarsen",
                        "spatial_support": int(signature_counts[window_signature]),
                        "db_refs": dict(bridge.db_refs),
                    }
                )
                assert source is not None
                source_rows_by_id[str(source_id)] = source.to_dict()

        self._multiscale_last_positions = current_positions
        self._bridge_records = next_records
        self._bridge_sources = next_sources
        self._trajectory_bodies = next_trajectory_bodies
        for verification in verification_rows:
            record = VerificationRun.from_dict(verification)
            next_verification_runs[str(record.verification_id)] = record
        self._verification_runs = next_verification_runs
        self._multiscale_last_tick = int(tick)
        self._multiscale_snapshots.append(
            {
                "tick": int(tick),
                "trace_ref": str(trace_ref),
                "energy": quantized_energy.copy(),
                "positions": current_positions,
            }
        )
        source_rows = list(source_rows_by_id.values())
        body_rows = list(body_rows_by_id.values())
        if self.bridge_source_store is not None:
            for source in source_rows:
                self.bridge_source_store.upsert(BridgeRecordSource.from_dict(source))
        if self.trajectory_body_store is not None:
            self.trajectory_body_store.replace_all(next_trajectory_bodies)
        if self.verification_run_store is not None:
            self.verification_run_store.replace_all(next_verification_runs)
        unique_signature_count = len(signature_counts)
        attractor_candidates = sum(1 for count in signature_counts.values() if int(count) >= candidate_threshold)
        return {
            "mode": str(self.multiscale_mode),
            "catalog_backend": self.multiscale_backend_info(),
            "candidates": candidate_rows,
            "sources": source_rows,
            "verifications": verification_rows,
            "summary": {
                "coarsen_candidate_count": int(len(candidate_rows)),
                "refine_candidate_count": int(refine_candidates),
                "attractor_candidate_count": int(attractor_candidates),
                "window_count": int(len(windows)),
                "unique_window_signature_count": int(unique_signature_count),
            },
            "hit_count": int(repeated_hits),
            "miss_count": int(max(0, len(windows) - repeated_hits)),
            "record_count": int(len(self._bridge_records)),
            "source_count": int(len(self._bridge_sources)),
            "body_count": int(len(self._trajectory_bodies)),
            "verification_run_count": int(len(self._verification_runs)),
            "bodies": body_rows,
        }

    def _is_reusable_record(self, record: PatternRecord) -> bool:
        return _is_reusable_record_flow(
            record=record,
            prune_error_threshold=float(self.prune_error_threshold),
            prune_deviation_threshold=float(self.prune_deviation_threshold),
        )

    @staticmethod
    def _interface_descriptor(interface_patch: np.ndarray) -> np.ndarray:
        patch = np.asarray(interface_patch, dtype=float)
        if patch.ndim != 2 or patch.shape[0] < 2 or patch.shape[1] < 2:
            return np.asarray([float(np.mean(patch))], dtype=float)
        top = float(np.mean(patch[0, :]))
        bottom = float(np.mean(patch[-1, :]))
        left = float(np.mean(patch[:, 0]))
        right = float(np.mean(patch[:, -1]))
        return np.asarray([top, right, bottom, left], dtype=float)

    @staticmethod
    def _normalize_context_token(value: str) -> str:
        return _normalize_context_token_flow(value)

    def _scoped_key(self, *, base_key: str, level: str, mode: str) -> str:
        return _scoped_key_flow(base_key=base_key, level=level, mode=mode)

    def _lookup_candidates(self, *, base_key: str, level: str, mode: str) -> tuple[str, ...]:
        return _lookup_candidates_flow(
            base_key=base_key,
            level=level,
            mode=mode,
            scope=str(self.reuse_scope),
        )

    def _remember_key(self, *, base_key: str, level: str, mode: str) -> str:
        return _remember_key_flow(
            base_key=base_key,
            level=level,
            mode=mode,
            scope=str(self.reuse_scope),
        )

    @staticmethod
    def _extract_patch(energy: np.ndarray, *, center_x: int, center_y: int, radius: int, boundary: str) -> np.ndarray:
        return _extract_patch_flow(
            energy,
            center_x=center_x,
            center_y=center_y,
            radius=radius,
            boundary=boundary,
        )


def get_pattern_runtime_for_state(*, state: Any, config: Any) -> PatternMemoryRuntime:
    runtime_key = _runtime_key_from_config_flow(config)
    existing = getattr(state, "_pattern_runtime", None)
    existing_key = getattr(state, "_pattern_runtime_key", None)
    if existing is not None and existing_key == runtime_key:
        return existing

    runtime = PatternMemoryRuntime(
        reuse_enabled=bool(runtime_key[0]),
        reuse_scope=str(runtime_key[1]),
        cache_capacity=int(runtime_key[2]),
        cache_ttl_steps=int(runtime_key[3]),
        prune_error_threshold=float(runtime_key[4]),
        prune_deviation_threshold=float(runtime_key[5]),
        store_path=runtime_key[6],
        multiscale_enabled=bool(runtime_key[7]),
        multiscale_mode=str(runtime_key[8]),
        multiscale_redis_url=runtime_key[9],
        multiscale_window_ticks=int(runtime_key[10]),
        multiscale_patch_radius=int(runtime_key[11]),
        multiscale_horizons=tuple(int(value) for value in tuple(runtime_key[12])),
        multiscale_quantization=float(runtime_key[13]),
        multiscale_candidate_min_support=int(runtime_key[14]),
        multiscale_candidate_min_confidence=float(runtime_key[15]),
        multiscale_jump_max_error=float(runtime_key[16]),
        multiscale_commit_only_sampling=bool(runtime_key[17]),
    )
    setattr(state, "_pattern_runtime", runtime)
    setattr(state, "_pattern_runtime_key", runtime_key)
    return runtime


__all__ = ["PatternMemoryRuntime", "get_pattern_runtime_for_state"]
