"""Runtime composition for quorum policy, validator registry, and ack aggregation."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping, Sequence

from detm.runtime.fabric import AckEnvelopeConsumer
from detm.runtime.fabric import FabricEnvelope
from detm.runtime.fabric import (
    AckResolver,
    BasicQuorumPolicy,
    InMemoryQuorumCoordinator,
    ValidatorSetQuorumPolicy,
)
from detm.runtime.fabric import StaticValidatorRegistry, ValidatorRegistry
from detm.runtime.fabric.quorum.resolver import ack_from_envelope_inline

# ARCH-MARKERS:
# - LAYER_BAND: L5
# - ABSTRACT_DISTANCE: 0 (runtime composition extracted; subscriber no longer builds quorum policy directly)
# - OOP_TECH_DEBT: distributed membership and replicated quorum-state persistence


@dataclass
class FabricQuorumRuntimeService(AckEnvelopeConsumer):
    """Composes validator membership + quorum policy into a runtime-facing service."""

    coordinator: InMemoryQuorumCoordinator
    validator_registry: ValidatorRegistry
    enforce_active_validator_membership: bool = False
    enforce_ack_sender_validator_match: bool = False
    enforce_ack_auth_key_id_binding: bool = False
    validator_auth_key_ids: dict[str, frozenset[str]] = field(default_factory=dict)
    enforce_ack_transport_identity_binding: bool = False
    validator_transport_identities: dict[str, frozenset[str]] = field(default_factory=dict)
    dropped_inactive_validator_total: int = 0
    dropped_sender_mismatch_total: int = 0
    dropped_invalid_inline_ack_total: int = 0
    dropped_missing_auth_key_id_total: int = 0
    dropped_auth_key_id_mismatch_total: int = 0
    dropped_missing_transport_identity_total: int = 0
    dropped_transport_identity_mismatch_total: int = 0
    validator_coordination_state_path: str | None = None
    validator_coordination_replica_paths: tuple[str, ...] = field(default_factory=tuple)
    validator_coordination_replica_read_quorum: int | None = None
    validator_coordination_replica_write_quorum: int | None = None
    validator_coordination_generation: int = 0
    validator_coordination_mode: str = "memory"
    validator_coordination_read_quorum_reached: bool = False
    validator_coordination_write_quorum_reached: bool = False
    validator_coordination_last_sync_error: str | None = None
    validator_coordination_last_sync_ts_ms: int = 0

    def __post_init__(self) -> None:
        self._load_validator_coordination_state()

    @classmethod
    def from_policy_settings(
        cls,
        *,
        required_proof_accepts: int = 1,
        required_trust_accepts: int = 1,
        required_unique_proof_validators: int = 1,
        required_unique_trust_validators: int = 1,
        required_validator_ids: Sequence[str] | None = None,
        enforce_required_validator_ids: bool = False,
        reject_on_any_reject: bool = False,
        pending_timeout_ms: int | None = None,
        ack_resolver: AckResolver | None = None,
        enforce_active_validator_membership: bool = False,
        enforce_ack_sender_validator_match: bool = False,
        enforce_ack_auth_key_id_binding: bool = False,
        validator_auth_key_ids: Mapping[str, Sequence[str] | str] | None = None,
        enforce_ack_transport_identity_binding: bool = False,
        validator_transport_identities: Mapping[str, Sequence[str] | str] | None = None,
        validator_coordination_state_path: str | None = None,
        validator_coordination_replica_paths: Sequence[str] | None = None,
        validator_coordination_replica_read_quorum: int | None = None,
        validator_coordination_replica_write_quorum: int | None = None,
    ) -> "FabricQuorumRuntimeService":
        registry = StaticValidatorRegistry.from_ids(required_validator_ids)
        auth_key_ids = _normalize_validator_auth_key_ids(validator_auth_key_ids)
        transport_identities = _normalize_validator_auth_key_ids(validator_transport_identities)
        if bool(enforce_ack_auth_key_id_binding) and not auth_key_ids:
            raise ValueError("validator_auth_key_ids must be non-empty when enforce_ack_auth_key_id_binding=true")
        if bool(enforce_ack_transport_identity_binding) and not transport_identities:
            raise ValueError(
                "validator_transport_identities must be non-empty when enforce_ack_transport_identity_binding=true"
            )
        validator_set = sorted(registry.required_validator_ids())
        if (
            int(required_unique_proof_validators) > 1
            or int(required_unique_trust_validators) > 1
            or bool(enforce_required_validator_ids)
            or len(validator_set) > 0
        ):
            policy = ValidatorSetQuorumPolicy(
                required_proof_accepts=int(required_proof_accepts),
                required_trust_accepts=int(required_trust_accepts),
                required_unique_proof_validators=int(required_unique_proof_validators),
                required_unique_trust_validators=int(required_unique_trust_validators),
                required_validator_ids=frozenset(validator_set),
                enforce_required_validator_ids=bool(enforce_required_validator_ids),
                reject_on_any_reject=bool(reject_on_any_reject),
            )
        else:
            policy = BasicQuorumPolicy(
                required_proof_accepts=int(required_proof_accepts),
                required_trust_accepts=int(required_trust_accepts),
                reject_on_any_reject=bool(reject_on_any_reject),
            )
        coordinator = InMemoryQuorumCoordinator(policy=policy, ack_resolver=ack_resolver)
        coordinator.pending_timeout_ms = pending_timeout_ms
        replica_paths = tuple(
            str(path).strip() for path in list(validator_coordination_replica_paths or []) if str(path).strip()
        )
        return cls(
            coordinator=coordinator,
            validator_registry=registry,
            enforce_active_validator_membership=bool(enforce_active_validator_membership),
            enforce_ack_sender_validator_match=bool(enforce_ack_sender_validator_match),
            enforce_ack_auth_key_id_binding=bool(enforce_ack_auth_key_id_binding),
            validator_auth_key_ids=auth_key_ids,
            enforce_ack_transport_identity_binding=bool(enforce_ack_transport_identity_binding),
            validator_transport_identities=transport_identities,
            validator_coordination_state_path=(
                None
                if validator_coordination_state_path is None or not str(validator_coordination_state_path).strip()
                else str(validator_coordination_state_path).strip()
            ),
            validator_coordination_replica_paths=replica_paths,
            validator_coordination_replica_read_quorum=(
                None
                if validator_coordination_replica_read_quorum is None
                else max(1, int(validator_coordination_replica_read_quorum))
            ),
            validator_coordination_replica_write_quorum=(
                None
                if validator_coordination_replica_write_quorum is None
                else max(1, int(validator_coordination_replica_write_quorum))
            ),
        )

    def register_commit(self, commit_ref: str, *, created_at_ms: int | None = None) -> None:
        self.coordinator.register_commit(str(commit_ref), created_at_ms=created_at_ms)
        self._persist_validator_coordination_state()

    def on_ack_envelope(self, envelope: FabricEnvelope) -> None:
        sender_id = str(envelope.sender).strip()
        ack_inline = ack_from_envelope_inline(envelope)
        ack_any = ack_inline
        if ack_any is None and self.coordinator.ack_resolver is not None:
            try:
                ack_any = self.coordinator.ack_resolver(str(envelope.payload_ref))
            except Exception:
                ack_any = None
        validator_id = None
        if ack_any is not None:
            validator_id = str(getattr(ack_any, "validator_id", "")).strip() or None
        if validator_id is None:
            validator_id = sender_id or None
        if bool(self.enforce_ack_sender_validator_match) and ack_any is not None:
            if not sender_id or sender_id != str(validator_id or ""):
                self.dropped_sender_mismatch_total += 1
                self._persist_validator_coordination_state()
                return
        if bool(self.enforce_ack_sender_validator_match) and ack_inline is None and bool(envelope.payload_inline):
            self.dropped_invalid_inline_ack_total += 1
            self._persist_validator_coordination_state()
            return
        if bool(self.enforce_active_validator_membership):
            required_ids = self.validator_registry.required_validator_ids()
            if required_ids:
                if validator_id is None or not self.validator_registry.is_active(str(validator_id)):
                    self.dropped_inactive_validator_total += 1
                    self._persist_validator_coordination_state()
                    return
        if bool(self.enforce_ack_auth_key_id_binding):
            raw_key_id = getattr(envelope, "auth_key_id", None)
            key_id = None if raw_key_id is None else str(raw_key_id).strip() or None
            allowed = self.validator_auth_key_ids.get(str(validator_id or "").strip(), frozenset())
            if key_id is None:
                self.dropped_missing_auth_key_id_total += 1
                self._persist_validator_coordination_state()
                return
            if not allowed or key_id not in allowed:
                self.dropped_auth_key_id_mismatch_total += 1
                self._persist_validator_coordination_state()
                return
        if bool(self.enforce_ack_transport_identity_binding):
            raw_transport_identity = getattr(envelope, "transport_identity", None)
            transport_identity = None if raw_transport_identity is None else str(raw_transport_identity).strip() or None
            allowed_transport = self.validator_transport_identities.get(str(validator_id or "").strip(), frozenset())
            if transport_identity is None:
                self.dropped_missing_transport_identity_total += 1
                self._persist_validator_coordination_state()
                return
            if not allowed_transport or transport_identity not in allowed_transport:
                self.dropped_transport_identity_mismatch_total += 1
                self._persist_validator_coordination_state()
                return
        self.coordinator.on_ack_envelope(envelope)
        self._persist_validator_coordination_state()

    def snapshot(self) -> dict[str, object]:
        out = dict(self.coordinator.snapshot())
        out["validator_registry"] = self.validator_registry.to_dict()
        out["pending_timeout_ms"] = (
            None if self.coordinator.pending_timeout_ms is None else int(self.coordinator.pending_timeout_ms)
        )
        out["membership_hardening"] = {
            "enforce_active_validator_membership": bool(self.enforce_active_validator_membership),
            "enforce_ack_sender_validator_match": bool(self.enforce_ack_sender_validator_match),
            "enforce_ack_auth_key_id_binding": bool(self.enforce_ack_auth_key_id_binding),
            "enforce_ack_transport_identity_binding": bool(self.enforce_ack_transport_identity_binding),
            "dropped_inactive_validator_total": int(self.dropped_inactive_validator_total),
            "dropped_sender_mismatch_total": int(self.dropped_sender_mismatch_total),
            "dropped_invalid_inline_ack_total": int(self.dropped_invalid_inline_ack_total),
            "dropped_missing_auth_key_id_total": int(self.dropped_missing_auth_key_id_total),
            "dropped_auth_key_id_mismatch_total": int(self.dropped_auth_key_id_mismatch_total),
            "dropped_missing_transport_identity_total": int(self.dropped_missing_transport_identity_total),
            "dropped_transport_identity_mismatch_total": int(self.dropped_transport_identity_mismatch_total),
            "registry_validator_count": int(len(self.validator_registry.required_validator_ids())),
            "validator_auth_key_ids": {
                str(validator_id): sorted(str(key_id) for key_id in key_ids)
                for validator_id, key_ids in sorted(self.validator_auth_key_ids.items())
            },
            "validator_transport_identities": {
                str(validator_id): sorted(str(identity) for identity in identities)
                for validator_id, identities in sorted(self.validator_transport_identities.items())
            },
        }
        out["validator_coordination_state"] = self._validator_coordination_snapshot()
        return out

    def _validator_coordination_snapshot(self) -> dict[str, object]:
        paths = self._validator_coordination_paths()
        read_quorum, write_quorum = self._validator_coordination_quorums(len(paths))
        if len(paths) == 0:
            return {
                "enabled": False,
                "mode": "memory",
                "state_path": None,
                "replica_paths": [],
                "read_quorum": 0,
                "write_quorum": 0,
                "read_quorum_reached": False,
                "write_quorum_reached": False,
                "generation": int(self.validator_coordination_generation),
                "last_sync_ts_ms": int(self.validator_coordination_last_sync_ts_ms),
                "last_sync_error": self.validator_coordination_last_sync_error,
            }
        return {
            "enabled": True,
            "mode": str(self.validator_coordination_mode),
            "state_path": str(paths[0]) if len(paths) == 1 else None,
            "replica_paths": [str(path) for path in paths] if len(paths) > 1 else [],
            "read_quorum": int(read_quorum),
            "write_quorum": int(write_quorum),
            "read_quorum_reached": bool(self.validator_coordination_read_quorum_reached),
            "write_quorum_reached": bool(self.validator_coordination_write_quorum_reached),
            "generation": int(self.validator_coordination_generation),
            "last_sync_ts_ms": int(self.validator_coordination_last_sync_ts_ms),
            "last_sync_error": self.validator_coordination_last_sync_error,
        }

    def _validator_coordination_paths(self) -> list[Path]:
        replica_paths = [Path(str(path).strip()) for path in list(self.validator_coordination_replica_paths or []) if str(path).strip()]
        if replica_paths:
            return replica_paths
        if self.validator_coordination_state_path is None:
            return []
        text = str(self.validator_coordination_state_path).strip()
        if not text:
            return []
        return [Path(text)]

    def _validator_coordination_quorums(self, replica_count: int) -> tuple[int, int]:
        if int(replica_count) <= 0:
            return 0, 0
        if int(replica_count) == 1:
            return 1, 1
        default_quorum = int(replica_count // 2) + 1
        read_quorum = (
            default_quorum
            if self.validator_coordination_replica_read_quorum is None
            else int(self.validator_coordination_replica_read_quorum)
        )
        write_quorum = (
            default_quorum
            if self.validator_coordination_replica_write_quorum is None
            else int(self.validator_coordination_replica_write_quorum)
        )
        return (
            max(1, min(int(replica_count), int(read_quorum))),
            max(1, min(int(replica_count), int(write_quorum))),
        )

    def _load_validator_coordination_state(self) -> None:
        paths = self._validator_coordination_paths()
        self.validator_coordination_mode = (
            "memory" if len(paths) == 0 else ("single_file" if len(paths) == 1 else "replicated")
        )
        if len(paths) == 0:
            return

        rows: list[dict[str, object]] = []
        read_errors: list[str] = []
        for path in paths:
            if not path.exists():
                continue
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    rows.append(dict(payload))
            except Exception as exc:
                read_errors.append(f"{path}: {exc}")

        read_quorum, _write_quorum = self._validator_coordination_quorums(len(paths))
        reached = bool(len(rows) >= read_quorum)
        if len(paths) == 1:
            reached = bool(len(rows) >= 1)
        self.validator_coordination_read_quorum_reached = reached
        if not reached:
            if read_errors:
                self.validator_coordination_last_sync_error = "; ".join(read_errors)
            elif len(paths) > 1:
                self.validator_coordination_last_sync_error = (
                    f"validator coordination read quorum not reached ({len(rows)}/{read_quorum})"
                )
            return
        if not rows:
            return

        rows = sorted(
            rows,
            key=lambda row: (
                int(dict(row).get("generation", 0)),
                int(dict(row).get("updated_at_ms", 0)),
            ),
        )
        payload = dict(rows[-1])
        payload_validator_ids = sorted(str(v) for v in list(payload.get("required_validator_ids", [])))
        current_validator_ids = sorted(str(v) for v in self.validator_registry.required_validator_ids())
        if payload_validator_ids and payload_validator_ids != current_validator_ids:
            self.validator_coordination_last_sync_error = (
                "validator coordination state validator-set mismatch; ignoring persisted counters"
            )
            return
        hardening = dict(payload.get("membership_hardening_counts", {}))
        self.dropped_inactive_validator_total = max(0, int(hardening.get("dropped_inactive_validator_total", 0)))
        self.dropped_sender_mismatch_total = max(0, int(hardening.get("dropped_sender_mismatch_total", 0)))
        self.dropped_invalid_inline_ack_total = max(0, int(hardening.get("dropped_invalid_inline_ack_total", 0)))
        self.dropped_missing_auth_key_id_total = max(0, int(hardening.get("dropped_missing_auth_key_id_total", 0)))
        self.dropped_auth_key_id_mismatch_total = max(0, int(hardening.get("dropped_auth_key_id_mismatch_total", 0)))
        self.dropped_missing_transport_identity_total = max(
            0,
            int(hardening.get("dropped_missing_transport_identity_total", 0)),
        )
        self.dropped_transport_identity_mismatch_total = max(
            0,
            int(hardening.get("dropped_transport_identity_mismatch_total", 0)),
        )
        self.validator_coordination_generation = max(0, int(payload.get("generation", 0)))
        self.validator_coordination_last_sync_ts_ms = int(time.time() * 1000)
        self.validator_coordination_last_sync_error = None

    def _persist_validator_coordination_state(self) -> None:
        paths = self._validator_coordination_paths()
        if len(paths) == 0:
            return
        read_quorum, write_quorum = self._validator_coordination_quorums(len(paths))
        required_write = 1 if len(paths) == 1 else int(write_quorum)
        now_ms = int(time.time() * 1000)
        next_generation = int(self.validator_coordination_generation) + 1
        payload = {
            "schema_version": "detm.fabric.validator_coordination_state.v1",
            "generation": int(next_generation),
            "updated_at_ms": int(now_ms),
            "required_validator_ids": sorted(str(v) for v in self.validator_registry.required_validator_ids()),
            "membership_hardening_counts": {
                "dropped_inactive_validator_total": int(self.dropped_inactive_validator_total),
                "dropped_sender_mismatch_total": int(self.dropped_sender_mismatch_total),
                "dropped_invalid_inline_ack_total": int(self.dropped_invalid_inline_ack_total),
                "dropped_missing_auth_key_id_total": int(self.dropped_missing_auth_key_id_total),
                "dropped_auth_key_id_mismatch_total": int(self.dropped_auth_key_id_mismatch_total),
                "dropped_missing_transport_identity_total": int(self.dropped_missing_transport_identity_total),
                "dropped_transport_identity_mismatch_total": int(self.dropped_transport_identity_mismatch_total),
            },
        }
        written = 0
        write_errors: list[str] = []
        for path in paths:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                tmp_path = path.with_suffix(".tmp")
                tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
                tmp_path.replace(path)
                written += 1
            except Exception as exc:
                write_errors.append(f"{path}: {exc}")

        self.validator_coordination_write_quorum_reached = bool(int(written) >= int(required_write))
        if len(paths) == 1:
            self.validator_coordination_read_quorum_reached = bool(int(written) >= 1)
        else:
            self.validator_coordination_read_quorum_reached = bool(int(written) >= int(read_quorum))
        self.validator_coordination_last_sync_ts_ms = int(now_ms)
        if self.validator_coordination_write_quorum_reached:
            self.validator_coordination_generation = int(next_generation)
            self.validator_coordination_last_sync_error = None
        else:
            self.validator_coordination_last_sync_error = (
                f"validator coordination write quorum not reached ({written}/{required_write})"
            )
            if write_errors:
                self.validator_coordination_last_sync_error += f"; errors: {'; '.join(write_errors)}"


def _normalize_validator_auth_key_ids(
    raw: Mapping[str, Sequence[str] | str] | None,
) -> dict[str, frozenset[str]]:
    out: dict[str, set[str]] = {}
    if raw is None:
        return {}
    for raw_validator_id, raw_key_ids in dict(raw).items():
        validator_id = str(raw_validator_id).strip()
        if not validator_id:
            continue
        values: list[str]
        if isinstance(raw_key_ids, str):
            values = [chunk.strip() for chunk in raw_key_ids.split(",") if chunk.strip()]
        elif isinstance(raw_key_ids, Sequence):
            values = [str(chunk).strip() for chunk in list(raw_key_ids) if str(chunk).strip()]
        else:
            value = str(raw_key_ids).strip()
            values = [value] if value else []
        if not values:
            continue
        bucket = out.setdefault(validator_id, set())
        bucket.update(values)
    return {validator_id: frozenset(sorted(values)) for validator_id, values in out.items() if values}


__all__ = ["FabricQuorumRuntimeService"]
