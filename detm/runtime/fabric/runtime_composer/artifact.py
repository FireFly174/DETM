"""Artifact store/resolver builders for fabric runtime composition."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from detm.runtime.commit_packet import CommitPacket
from detm.runtime.fabric import FabricArtifactResolver, FileFabricArtifactStore, ProofAck, TrustAck


def build_artifact_components(
    *,
    rec: Any,
    commit_store: dict[str, CommitPacket],
    commit_ref_index: dict[str, str],
    ack_store: dict[str, ProofAck | TrustAck],
) -> tuple[FileFabricArtifactStore | None, FabricArtifactResolver]:
    artifact_store: FileFabricArtifactStore | None = None
    if rec.artifact_store_dir is not None:
        artifact_store = FileFabricArtifactStore(Path(rec.artifact_store_dir))
    artifact_resolver = FabricArtifactResolver(
        node_id=str(rec.node_id),
        artifact_store=artifact_store,
        commit_store=commit_store,
        commit_ref_index=commit_ref_index,
        ack_store=ack_store,
    )
    return artifact_store, artifact_resolver


__all__ = ["build_artifact_components"]
