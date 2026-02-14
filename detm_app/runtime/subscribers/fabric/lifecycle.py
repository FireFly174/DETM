"""Lifecycle helpers for FabricHandshakeRecorder runtime wiring."""

from __future__ import annotations

from typing import Any


def initialize_recorder_runtime_state(rec: Any, *, bus: Any) -> None:
    rec._commit_store = {}
    rec._commit_ref_index = {}
    rec._ack_store = {}
    rec._bus = bus
    rec._ack_envelopes = []
    rec._ack_subscriptions = []
    rec._delivery_ack_envelopes = []
    rec._delivery_ack_subscriptions = []
    rec._delivery_pending = {}
    rec._delivery_receipt_coordinator = None
    rec._delivery_tracker = None
    rec._delivery_accepted_count = 0
    rec._delivery_rejected_count = 0
    rec._delivery_retries_total = 0
    rec._delivery_counter = 0
    rec._commit_dead_letters = []
    rec._replay_checks_total = 0
    rec._replay_checks_failed = 0


def bind_runtime_composition(rec: Any, composition: Any) -> None:
    rec._commit_store = composition.commit_store
    rec._commit_ref_index = composition.commit_ref_index
    rec._ack_store = composition.ack_store
    rec._artifact_resolver = composition.artifact_resolver
    rec._ack_envelopes = composition.ack_envelopes
    rec._ack_subscriptions = composition.ack_subscriptions
    rec._delivery_ack_envelopes = composition.delivery_ack_envelopes
    rec._delivery_ack_subscriptions = composition.delivery_ack_subscriptions
    rec._delivery_pending = composition.delivery_pending
    rec._delivery_receipt_coordinator = composition.delivery_receipt_coordinator
    rec._delivery_tracker = composition.delivery_tracker
    rec._commit_dead_letters = composition.commit_dead_letters
    rec._artifact_store = composition.artifact_store
    rec._delivery_outbox = composition.delivery_outbox
    rec._transport = composition.transport
    rec._validator = composition.validator
    rec._epoch_coordinator = composition.epoch_coordinator
    rec._epoch_consensus = composition.epoch_consensus
    rec._quorum_runtime = composition.quorum_runtime
    rec._quorum = composition.quorum
    rec._validator_registry = composition.validator_registry
    rec._service = composition.service
    rec._ack_runtime = composition.ack_runtime
    rec._delivery_runtime = composition.delivery_runtime
    rec._commit_ingress = composition.commit_ingress
    rec._quorum_report_builder = composition.quorum_report_builder
    rec._fabric_report_writer = composition.fabric_report_writer
    rec._runtime_bundle = composition.runtime_bundle
    rec._start_runtime_bundle()


def clear_runtime_links(rec: Any) -> None:
    rec._service = None
    rec._ack_runtime = None
    rec._delivery_runtime = None
    rec._commit_ingress = None
    rec._transport = None
    rec._quorum_runtime = None
    rec._quorum_report_builder = None
    rec._fabric_report_writer = None
    rec._quorum = None
    rec._epoch_consensus = None
    rec._epoch_coordinator = None
    rec._validator_registry = None
    rec._artifact_store = None
    rec._artifact_resolver = None
    rec._delivery_outbox = None
    rec._delivery_tracker = None
    rec._delivery_receipt_coordinator = None
    rec._delivery_pending = {}
    rec._commit_ref_index = {}


__all__ = ["bind_runtime_composition", "clear_runtime_links", "initialize_recorder_runtime_state"]
