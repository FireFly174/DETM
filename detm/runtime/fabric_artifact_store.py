"""Durable artifact storage for fabric commit/ack payloads."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Protocol

from detm.runtime.commit_packet import CommitPacket
from detm.runtime.fabric_ack import ProofAck, TrustAck

# ARCH-MARKERS:
# - LAYER_BAND: L5
# - ABSTRACT_DISTANCE: 0 (artifact store abstraction exists)
# - OOP_TECH_DEBT: remote replicated store + retention/compaction policy


class FabricArtifactStore(Protocol):
    """Artifact storage contract for commit and ack payload references."""

    def write_commit(self, packet: CommitPacket, *, artifact_ref: str | None = None) -> str:
        ...

    def read_commit(self, artifact_ref: str) -> CommitPacket | None:
        ...

    def write_ack(self, ack: ProofAck | TrustAck, *, artifact_ref: str | None = None) -> str:
        ...

    def read_ack(self, artifact_ref: str) -> ProofAck | TrustAck | None:
        ...


def _ref_digest(artifact_ref: str) -> str:
    return hashlib.sha256(str(artifact_ref).encode("utf-8")).hexdigest()


@dataclass
class FileFabricArtifactStore:
    """Simple file-backed artifact store for shared commit/ack resolution."""

    root_dir: Path

    def __post_init__(self) -> None:
        self.root_dir = Path(self.root_dir)
        (self.root_dir / "commit").mkdir(parents=True, exist_ok=True)
        (self.root_dir / "ack").mkdir(parents=True, exist_ok=True)

    def write_commit(self, packet: CommitPacket, *, artifact_ref: str | None = None) -> str:
        ref = str(artifact_ref or f"artifact://commit/{packet.node_id}/{packet.commit_id}")
        self._write_record("commit", ref, packet.to_dict())
        return ref

    def read_commit(self, artifact_ref: str) -> CommitPacket | None:
        payload = self._read_payload("commit", str(artifact_ref))
        if payload is None:
            return None
        try:
            return CommitPacket.from_dict(payload)
        except Exception:
            return None

    def write_ack(self, ack: ProofAck | TrustAck, *, artifact_ref: str | None = None) -> str:
        ack_kind = "proof" if isinstance(ack, ProofAck) else "trust"
        ref = str(artifact_ref or f"artifact://ack/{ack.validator_id}/{ack.commit_ref}/{ack_kind}")
        self._write_record("ack", ref, ack.to_dict())
        return ref

    def read_ack(self, artifact_ref: str) -> ProofAck | TrustAck | None:
        payload = self._read_payload("ack", str(artifact_ref))
        if payload is None:
            return None
        ack_type = str(payload.get("ack_type", "")).strip().lower()
        try:
            if ack_type == "proof_ack":
                return ProofAck.from_dict(payload)
            if ack_type == "trust_ack":
                return TrustAck.from_dict(payload)
        except Exception:
            return None
        return None

    def _record_path(self, kind: str, artifact_ref: str) -> Path:
        return self.root_dir / str(kind) / f"{_ref_digest(artifact_ref)}.json"

    def _write_record(self, kind: str, artifact_ref: str, payload: Dict[str, Any]) -> None:
        path = self._record_path(kind, artifact_ref)
        row = {"kind": str(kind), "artifact_ref": str(artifact_ref), "payload": dict(payload)}
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(row, ensure_ascii=False), encoding="utf-8")
        tmp.replace(path)

    def _read_payload(self, kind: str, artifact_ref: str) -> Dict[str, Any] | None:
        path = self._record_path(kind, artifact_ref)
        if not path.exists():
            return None
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        if not isinstance(row, dict):
            return None
        payload = row.get("payload")
        if not isinstance(payload, dict):
            return None
        return dict(payload)

    def to_dict(self) -> Dict[str, Any]:
        return {"root_dir": str(self.root_dir)}


__all__ = ["FabricArtifactStore", "FileFabricArtifactStore"]
