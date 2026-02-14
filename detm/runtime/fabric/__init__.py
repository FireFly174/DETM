"""Canonical runtime fabric namespace with lazy compatibility exports."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_SYMBOL_TO_MODULE = {
    "ProofAck": "detm.runtime.fabric.ack",
    "TrustAck": "detm.runtime.fabric.ack",
    "AckEnvelopeConsumer": "detm.runtime.fabric.ack_ingress",
    "FabricAckIngressService": "detm.runtime.fabric.ack_ingress",
    "FabricArtifactResolver": "detm.runtime.fabric.artifact_resolver",
    "FabricArtifactStore": "detm.runtime.fabric.artifact_store",
    "FileFabricArtifactStore": "detm.runtime.fabric.artifact_store",
    "FabricCommitDeliveryService": "detm.runtime.fabric.commit_delivery",
    "FabricCommitIngressService": "detm.runtime.fabric.commit_ingress",
    "FabricEnvelopeOutbox": "detm.runtime.fabric.delivery",
    "JsonlFabricEnvelopeOutbox": "detm.runtime.fabric.delivery",
    "ReplicatedJsonlFabricEnvelopeOutbox": "detm.runtime.fabric.delivery",
    "OUTBOX_DROP_POLICIES": "detm.runtime.fabric.delivery",
    "DeliveryReceiptPolicy": "detm.runtime.fabric.delivery_receipts",
    "CountDeliveryReceiptPolicy": "detm.runtime.fabric.delivery_receipts",
    "ValidatorSetDeliveryReceiptPolicy": "detm.runtime.fabric.delivery_receipts",
    "InMemoryDeliveryReceiptCoordinator": "detm.runtime.fabric.delivery_receipts",
    "DeliveryTrackingCoordinator": "detm.runtime.fabric.delivery_tracking",
    "EpochDecision": "detm.runtime.fabric.epoch",
    "FabricEpochCoordinator": "detm.runtime.fabric.epoch",
    "FileEpochWatermarkCoordinator": "detm.runtime.fabric.epoch",
    "InMemoryEpochWatermarkCoordinator": "detm.runtime.fabric.epoch",
    "ReplicatedFileEpochWatermarkCoordinator": "detm.runtime.fabric.epoch",
    "commit_epoch": "detm.runtime.fabric.epoch",
    "commit_watermark": "detm.runtime.fabric.epoch",
    "TransportEpochConsensusCoordinator": "detm.runtime.fabric.epoch_consensus",
    "FabricEnvelope": "detm.runtime.fabric.envelope",
    "FabricValidator": "detm.runtime.fabric.validator",
    "LocalFabricValidator": "detm.runtime.fabric.validator",
    "ReplayChecker": "detm.runtime.fabric.validator",
    "ReplaySamplePolicy": "detm.runtime.fabric.validator",
    "ValidatorRegistry": "detm.runtime.fabric.validator_registry",
    "StaticValidatorRegistry": "detm.runtime.fabric.validator_registry",
    "FabricHandshakeService": "detm.runtime.fabric.handshake",
    "RetryPolicy": "detm.runtime.fabric.handshake",
    "normalize_fabric_handshake_recorder_attach_kwargs": "detm.runtime.fabric.handshake_recorder_config",
    "BACKPRESSURE_POLICIES": "detm.runtime.fabric.transport",
    "BufferedFabricTransport": "detm.runtime.fabric.transport",
    "InMemoryFabricBus": "detm.runtime.fabric.transport",
    "FabricTransportAdapter": "detm.runtime.fabric.transport",
    "FabricHandler": "detm.runtime.fabric.transport",
    "QuorumPolicy": "detm.runtime.fabric.quorum",
    "AckResolver": "detm.runtime.fabric.quorum",
    "BasicQuorumPolicy": "detm.runtime.fabric.quorum",
    "InMemoryQuorumCoordinator": "detm.runtime.fabric.quorum",
    "ValidatorSetQuorumPolicy": "detm.runtime.fabric.quorum",
    "FabricQuorumReportBuilder": "detm.runtime.fabric.quorum_report",
    "FabricQuorumRuntimeService": "detm.runtime.fabric.quorum_runtime",
    "FabricRuntimeReportWriter": "detm.runtime.fabric.report_writer",
    "FabricHandshakeRuntimeBundle": "detm.runtime.fabric.runtime_bundle",
    "FabricHandshakeRuntimeComposition": "detm.runtime.fabric.runtime_composer",
    "compose_fabric_handshake_runtime": "detm.runtime.fabric.runtime_composer",
    "mode_channels": "detm.runtime.fabric.runtime_helpers",
    "channel_for_mode": "detm.runtime.fabric.runtime_helpers",
    "start_runtime_bundle": "detm.runtime.fabric.runtime_helpers",
    "TcpFabricRelay": "detm.runtime.fabric.tcp_transport",
    "TcpFabricTransport": "detm.runtime.fabric.tcp_transport",
    "open_fabric_transport": "detm.runtime.fabric.tcp_transport",
    "validate_commit_paths": "detm.runtime.fabric.validation",
}

__all__ = sorted(_SYMBOL_TO_MODULE.keys())


def __getattr__(name: str) -> Any:
    target_module = _SYMBOL_TO_MODULE.get(name)
    if target_module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(target_module)
    value = getattr(module, name)
    globals()[name] = value
    return value
