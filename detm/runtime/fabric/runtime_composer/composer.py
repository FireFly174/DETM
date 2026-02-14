"""Factory/composer for fabric handshake runtime components."""

from __future__ import annotations

from typing import Any, Callable

from detm.runtime.fabric import FabricQuorumRuntimeService, InMemoryDeliveryReceiptCoordinator, open_fabric_transport
from detm.runtime.fabric.runtime_composer.artifact import build_artifact_components
from detm.runtime.fabric.runtime_composer.contracts import FabricHandshakeRuntimeComposition
from detm.runtime.fabric.runtime_composer.delivery import (
    build_delivery_outbox,
    build_delivery_receipt_policy,
    build_delivery_tracker,
)
from detm.runtime.fabric.runtime_composer.epoch import build_epoch_runtime
from detm.runtime.fabric.runtime_composer.quorum import build_quorum_runtime
from detm.runtime.fabric.runtime_composer.reporting import build_reporting_components
from detm.runtime.fabric.runtime_composer.services import build_service_stack
from detm.runtime.fabric.runtime_composer.state import init_composer_state
from detm.runtime.fabric.runtime_composer.transport import build_transport
from detm.runtime.fabric.runtime_composer.validator import build_validator

# ARCH-MARKERS:
# - LAYER_BAND: L5
# - ABSTRACT_DISTANCE: 0 (runtime composition extracted from subscriber attach path)
# - OOP_TECH_DEBT: distributed config/schema for runtime-composer presets


def compose_fabric_handshake_runtime(
    *,
    rec: Any,
    mode_channels: Callable[[str], dict[str, str] | None],
) -> FabricHandshakeRuntimeComposition:
    """Build runtime composition from normalized recorder settings."""

    state = init_composer_state(rec=rec)

    delivery_policy = build_delivery_receipt_policy(rec=rec)
    delivery_receipt_coordinator = InMemoryDeliveryReceiptCoordinator(policy=delivery_policy)
    delivery_tracker = build_delivery_tracker(
        rec=rec,
        delivery_pending=state.delivery_pending,
        delivery_tracking_state_path=state.delivery_tracking_state_path,
        delivery_receipt_coordinator=delivery_receipt_coordinator,
    )
    delivery_outbox = build_delivery_outbox(rec=rec)

    artifact_store, artifact_resolver = build_artifact_components(
        rec=rec,
        commit_store=state.commit_store,
        commit_ref_index=state.commit_ref_index,
        ack_store=state.ack_store,
    )

    # Kept in this module to preserve monkeypatch target used by regression tests.
    transport = build_transport(rec=rec, open_transport_fn=open_fabric_transport)
    validator = build_validator(rec=rec, artifact_resolver=artifact_resolver)
    epoch_coordinator, epoch_consensus = build_epoch_runtime(
        rec=rec,
        artifact_store=artifact_store,
        transport=transport,
    )

    # Kept in this module to preserve monkeypatch target used by regression tests.
    quorum_runtime, quorum, validator_registry = build_quorum_runtime(
        rec=rec,
        artifact_resolver=artifact_resolver,
        from_policy_settings=FabricQuorumRuntimeService.from_policy_settings,
    )

    service, ack_runtime, delivery_runtime, commit_ingress = build_service_stack(
        rec=rec,
        mode_channels=mode_channels,
        transport=transport,
        validator=validator,
        artifact_resolver=artifact_resolver,
        delivery_outbox=delivery_outbox,
        epoch_coordinator=epoch_coordinator,
        quorum_runtime=quorum_runtime,
        delivery_tracker=delivery_tracker,
        ack_envelopes=state.ack_envelopes,
        delivery_ack_envelopes=state.delivery_ack_envelopes,
        commit_dead_letters=state.commit_dead_letters,
    )

    quorum_report_builder, fabric_report_writer, runtime_bundle = build_reporting_components(
        rec=rec,
        mode_channels=mode_channels,
        quorum_runtime=quorum_runtime,
        artifact_store=artifact_store,
        transport=transport,
        delivery_outbox=delivery_outbox,
        delivery_runtime=delivery_runtime,
        epoch_coordinator=epoch_coordinator,
        epoch_consensus=epoch_consensus,
        service=service,
        ack_runtime=ack_runtime,
        ack_store=state.ack_store,
        ack_envelopes=state.ack_envelopes,
        delivery_ack_envelopes=state.delivery_ack_envelopes,
        commit_dead_letters=state.commit_dead_letters,
    )

    return FabricHandshakeRuntimeComposition(
        commit_store=state.commit_store,
        commit_ref_index=state.commit_ref_index,
        ack_store=state.ack_store,
        artifact_resolver=artifact_resolver,
        ack_envelopes=state.ack_envelopes,
        ack_subscriptions=state.ack_subscriptions,
        delivery_ack_envelopes=state.delivery_ack_envelopes,
        delivery_ack_subscriptions=state.delivery_ack_subscriptions,
        delivery_pending=state.delivery_pending,
        delivery_receipt_coordinator=delivery_receipt_coordinator,
        delivery_tracker=delivery_tracker,
        commit_dead_letters=state.commit_dead_letters,
        artifact_store=artifact_store,
        delivery_outbox=delivery_outbox,
        transport=transport,
        validator=validator,
        epoch_coordinator=epoch_coordinator,
        epoch_consensus=epoch_consensus,
        quorum_runtime=quorum_runtime,
        quorum=quorum,
        validator_registry=validator_registry,
        service=service,
        ack_runtime=ack_runtime,
        delivery_runtime=delivery_runtime,
        commit_ingress=commit_ingress,
        quorum_report_builder=quorum_report_builder,
        fabric_report_writer=fabric_report_writer,
        runtime_bundle=runtime_bundle,
    )


__all__ = ["FabricHandshakeRuntimeComposition", "compose_fabric_handshake_runtime"]
