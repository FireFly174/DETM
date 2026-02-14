"""Composition contracts for fabric runtime assembly."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from detm.runtime.commit_packet import CommitPacket
from detm.runtime.fabric import ProofAck, TrustAck
from detm.runtime.fabric import FabricAckIngressService
from detm.runtime.fabric import FabricArtifactResolver
from detm.runtime.fabric import FileFabricArtifactStore
from detm.runtime.fabric import FabricCommitDeliveryService
from detm.runtime.fabric import FabricCommitIngressService
from detm.runtime.fabric import FabricEnvelopeOutbox
from detm.runtime.fabric import InMemoryDeliveryReceiptCoordinator
from detm.runtime.fabric import DeliveryTrackingCoordinator
from detm.runtime.fabric import FabricEpochCoordinator
from detm.runtime.fabric import TransportEpochConsensusCoordinator
from detm.runtime.fabric import FabricEnvelope
from detm.runtime.fabric import FabricHandshakeService
from detm.runtime.fabric import InMemoryQuorumCoordinator
from detm.runtime.fabric import FabricQuorumReportBuilder
from detm.runtime.fabric import FabricQuorumRuntimeService
from detm.runtime.fabric import FabricRuntimeReportWriter
from detm.runtime.fabric import FabricHandshakeRuntimeBundle
from detm.runtime.fabric import FabricTransportAdapter
from detm.runtime.fabric import LocalFabricValidator
from detm.runtime.fabric import ValidatorRegistry


@dataclass
class FabricHandshakeRuntimeComposition:
    """Assembled runtime components used by FabricHandshakeRecorder."""

    commit_store: dict[str, CommitPacket]
    commit_ref_index: dict[str, str]
    ack_store: dict[str, ProofAck | TrustAck]
    artifact_resolver: FabricArtifactResolver
    ack_envelopes: list[FabricEnvelope]
    ack_subscriptions: list[tuple[str, str | None]]
    delivery_ack_envelopes: list[FabricEnvelope]
    delivery_ack_subscriptions: list[tuple[str, str | None]]
    delivery_pending: dict[str, dict[str, Any]]
    delivery_receipt_coordinator: InMemoryDeliveryReceiptCoordinator
    delivery_tracker: DeliveryTrackingCoordinator
    commit_dead_letters: list[dict[str, str]]
    artifact_store: FileFabricArtifactStore | None
    delivery_outbox: FabricEnvelopeOutbox
    transport: FabricTransportAdapter
    validator: LocalFabricValidator
    epoch_coordinator: FabricEpochCoordinator
    epoch_consensus: TransportEpochConsensusCoordinator | None
    quorum_runtime: FabricQuorumRuntimeService
    quorum: InMemoryQuorumCoordinator
    validator_registry: ValidatorRegistry
    service: FabricHandshakeService
    ack_runtime: FabricAckIngressService
    delivery_runtime: FabricCommitDeliveryService
    commit_ingress: FabricCommitIngressService
    quorum_report_builder: FabricQuorumReportBuilder
    fabric_report_writer: FabricRuntimeReportWriter
    runtime_bundle: FabricHandshakeRuntimeBundle


__all__ = ["FabricHandshakeRuntimeComposition"]


