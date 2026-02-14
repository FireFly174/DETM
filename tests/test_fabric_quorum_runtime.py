from __future__ import annotations

import json

import pytest

from detm.runtime.fabric import ProofAck, TrustAck
from detm.runtime.fabric import FabricEnvelope
from detm.runtime.fabric import FabricQuorumRuntimeService


def _proof_env(commit_ref: str, validator_id: str, *, auth_key_id: str | None = None) -> FabricEnvelope:
    ack = ProofAck(
        validator_id=validator_id,
        node_id="node-A",
        commit_ref=commit_ref,
        status="accepted",
        signature=f"sig://{validator_id}/proof/{commit_ref}",
    )
    return FabricEnvelope.from_dict(
        {
            "message_type": "proof_ack",
            "channel": "fabric.ack",
            "mode": "realtime",
            "sender": validator_id,
            "payload_ref": f"artifact://ack/{validator_id}/proof/{commit_ref}",
            "payload_inline": ack.to_dict(),
            "commit_ref": commit_ref,
            "auth_key_id": auth_key_id,
            "transport_identity": f"cn:{validator_id}",
        }
    )


def _trust_env(commit_ref: str, validator_id: str, *, auth_key_id: str | None = None) -> FabricEnvelope:
    ack = TrustAck(
        validator_id=validator_id,
        node_id="node-A",
        commit_ref=commit_ref,
        status="accepted",
        signature=f"sig://{validator_id}/trust/{commit_ref}",
    )
    return FabricEnvelope.from_dict(
        {
            "message_type": "trust_ack",
            "channel": "fabric.ack",
            "mode": "realtime",
            "sender": validator_id,
            "payload_ref": f"artifact://ack/{validator_id}/trust/{commit_ref}",
            "payload_inline": ack.to_dict(),
            "commit_ref": commit_ref,
            "auth_key_id": auth_key_id,
            "transport_identity": f"cn:{validator_id}",
        }
    )


def test_quorum_runtime_snapshot_includes_registry_and_pending_timeout():
    runtime = FabricQuorumRuntimeService.from_policy_settings(
        required_proof_accepts=1,
        required_trust_accepts=1,
        pending_timeout_ms=123,
    )
    runtime.register_commit("node-A:1")
    runtime.on_ack_envelope(_proof_env("node-A:1", "validator-1"))
    runtime.on_ack_envelope(_trust_env("node-A:1", "validator-1"))

    snap = runtime.snapshot()
    assert int(snap["accepted_count"]) == 1
    assert snap["pending_timeout_ms"] == 123
    assert dict(snap["validator_registry"]) == {"validators": []}
    hardening = dict(snap["membership_hardening"])
    assert bool(hardening["enforce_active_validator_membership"]) is False
    assert bool(hardening["enforce_ack_sender_validator_match"]) is False
    assert bool(hardening["enforce_ack_auth_key_id_binding"]) is False
    assert bool(hardening["enforce_ack_transport_identity_binding"]) is False


def test_quorum_runtime_enforces_validator_set_policy():
    runtime = FabricQuorumRuntimeService.from_policy_settings(
        required_proof_accepts=1,
        required_trust_accepts=1,
        required_unique_proof_validators=1,
        required_unique_trust_validators=1,
        required_validator_ids=["validator-1", "validator-2"],
        enforce_required_validator_ids=True,
    )
    runtime.register_commit("node-A:2")
    runtime.on_ack_envelope(_proof_env("node-A:2", "validator-1"))
    runtime.on_ack_envelope(_trust_env("node-A:2", "validator-1"))

    snap = runtime.snapshot()
    assert int(snap["accepted_count"]) == 0
    assert int(snap["pending_count"]) == 1
    row = list(snap["evaluations"])[0]
    assert "required validator set missing" in str(row["reason"])


def test_quorum_runtime_membership_hardening_drops_inactive_validators():
    runtime = FabricQuorumRuntimeService.from_policy_settings(
        required_proof_accepts=1,
        required_trust_accepts=1,
        required_validator_ids=["validator-1"],
        enforce_active_validator_membership=True,
    )
    runtime.register_commit("node-A:3")
    runtime.on_ack_envelope(_proof_env("node-A:3", "validator-unknown"))
    runtime.on_ack_envelope(_trust_env("node-A:3", "validator-unknown"))

    snap = runtime.snapshot()
    assert int(snap["accepted_count"]) == 0
    assert int(snap["pending_count"]) == 1
    hardening = dict(snap["membership_hardening"])
    assert int(hardening["dropped_inactive_validator_total"]) == 2
    assert int(hardening["dropped_sender_mismatch_total"]) == 0


def test_quorum_runtime_membership_hardening_drops_sender_mismatch():
    runtime = FabricQuorumRuntimeService.from_policy_settings(
        required_proof_accepts=1,
        required_trust_accepts=1,
        required_validator_ids=["validator-1"],
        enforce_active_validator_membership=True,
        enforce_ack_sender_validator_match=True,
    )
    runtime.register_commit("node-A:4")
    bad_sender_proof = _proof_env("node-A:4", "validator-1").to_dict()
    bad_sender_proof["sender"] = "validator-spoof"
    runtime.on_ack_envelope(FabricEnvelope.from_dict(bad_sender_proof))
    runtime.on_ack_envelope(_trust_env("node-A:4", "validator-1"))

    snap = runtime.snapshot()
    assert int(snap["accepted_count"]) == 0
    assert int(snap["pending_count"]) == 1
    hardening = dict(snap["membership_hardening"])
    assert int(hardening["dropped_sender_mismatch_total"]) == 1


def test_quorum_runtime_auth_key_id_binding_accepts_matching_validator_mapping():
    runtime = FabricQuorumRuntimeService.from_policy_settings(
        required_proof_accepts=1,
        required_trust_accepts=1,
        required_validator_ids=["validator-1"],
        enforce_active_validator_membership=True,
        enforce_ack_auth_key_id_binding=True,
        validator_auth_key_ids={"validator-1": ["kid-1"]},
    )
    runtime.register_commit("node-A:5")
    runtime.on_ack_envelope(_proof_env("node-A:5", "validator-1", auth_key_id="kid-1"))
    runtime.on_ack_envelope(_trust_env("node-A:5", "validator-1", auth_key_id="kid-1"))

    snap = runtime.snapshot()
    assert int(snap["accepted_count"]) == 1
    hardening = dict(snap["membership_hardening"])
    assert int(hardening["dropped_missing_auth_key_id_total"]) == 0
    assert int(hardening["dropped_auth_key_id_mismatch_total"]) == 0


def test_quorum_runtime_auth_key_id_binding_drops_missing_or_mismatched_key_id():
    runtime = FabricQuorumRuntimeService.from_policy_settings(
        required_proof_accepts=1,
        required_trust_accepts=1,
        required_validator_ids=["validator-1"],
        enforce_active_validator_membership=True,
        enforce_ack_auth_key_id_binding=True,
        validator_auth_key_ids={"validator-1": ["kid-1"]},
    )
    runtime.register_commit("node-A:6")
    missing_key = _proof_env("node-A:6", "validator-1", auth_key_id=None).to_dict()
    missing_key.pop("auth_key_id", None)
    runtime.on_ack_envelope(FabricEnvelope.from_dict(missing_key))
    runtime.on_ack_envelope(_trust_env("node-A:6", "validator-1", auth_key_id="kid-bad"))

    snap = runtime.snapshot()
    assert int(snap["accepted_count"]) == 0
    assert int(snap["pending_count"]) == 1
    hardening = dict(snap["membership_hardening"])
    assert int(hardening["dropped_missing_auth_key_id_total"]) == 1
    assert int(hardening["dropped_auth_key_id_mismatch_total"]) == 1


def test_quorum_runtime_auth_key_id_binding_requires_non_empty_mapping():
    with pytest.raises(ValueError, match="validator_auth_key_ids must be non-empty"):
        FabricQuorumRuntimeService.from_policy_settings(
            enforce_ack_auth_key_id_binding=True,
            validator_auth_key_ids={},
        )


def test_quorum_runtime_transport_identity_binding_accepts_matching_mapping():
    runtime = FabricQuorumRuntimeService.from_policy_settings(
        required_proof_accepts=1,
        required_trust_accepts=1,
        required_validator_ids=["validator-1"],
        enforce_active_validator_membership=True,
        enforce_ack_transport_identity_binding=True,
        validator_transport_identities={"validator-1": ["cn:validator-1"]},
    )
    runtime.register_commit("node-A:7")
    runtime.on_ack_envelope(_proof_env("node-A:7", "validator-1", auth_key_id=None))
    runtime.on_ack_envelope(_trust_env("node-A:7", "validator-1", auth_key_id=None))

    snap = runtime.snapshot()
    assert int(snap["accepted_count"]) == 1
    hardening = dict(snap["membership_hardening"])
    assert int(hardening["dropped_missing_transport_identity_total"]) == 0
    assert int(hardening["dropped_transport_identity_mismatch_total"]) == 0


def test_quorum_runtime_transport_identity_binding_drops_missing_or_mismatched():
    runtime = FabricQuorumRuntimeService.from_policy_settings(
        required_proof_accepts=1,
        required_trust_accepts=1,
        required_validator_ids=["validator-1"],
        enforce_active_validator_membership=True,
        enforce_ack_transport_identity_binding=True,
        validator_transport_identities={"validator-1": ["cn:validator-1"]},
    )
    runtime.register_commit("node-A:8")
    missing_identity = _proof_env("node-A:8", "validator-1", auth_key_id=None).to_dict()
    missing_identity.pop("transport_identity", None)
    runtime.on_ack_envelope(FabricEnvelope.from_dict(missing_identity))
    mismatched_identity = _trust_env("node-A:8", "validator-1", auth_key_id=None).to_dict()
    mismatched_identity["transport_identity"] = "cn:other"
    runtime.on_ack_envelope(FabricEnvelope.from_dict(mismatched_identity))

    snap = runtime.snapshot()
    assert int(snap["accepted_count"]) == 0
    assert int(snap["pending_count"]) == 1
    hardening = dict(snap["membership_hardening"])
    assert int(hardening["dropped_missing_transport_identity_total"]) == 1
    assert int(hardening["dropped_transport_identity_mismatch_total"]) == 1


def test_quorum_runtime_transport_identity_binding_requires_non_empty_mapping():
    with pytest.raises(ValueError, match="validator_transport_identities must be non-empty"):
        FabricQuorumRuntimeService.from_policy_settings(
            enforce_ack_transport_identity_binding=True,
            validator_transport_identities={},
        )


def test_quorum_runtime_persists_and_restores_validator_coordination_single_file(tmp_path):
    state_path = tmp_path / "validator_coordination_state.json"
    runtime = FabricQuorumRuntimeService.from_policy_settings(
        required_proof_accepts=1,
        required_trust_accepts=1,
        required_validator_ids=["validator-1"],
        enforce_active_validator_membership=True,
        validator_coordination_state_path=str(state_path),
    )
    runtime.register_commit("node-A:coord:single")
    runtime.on_ack_envelope(_proof_env("node-A:coord:single", "validator-unknown"))

    assert state_path.exists()
    payload = json.loads(state_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "detm.fabric.validator_coordination_state.v1"
    hardening = dict(payload["membership_hardening_counts"])
    assert int(hardening["dropped_inactive_validator_total"]) == 1

    restored = FabricQuorumRuntimeService.from_policy_settings(
        required_proof_accepts=1,
        required_trust_accepts=1,
        required_validator_ids=["validator-1"],
        enforce_active_validator_membership=True,
        validator_coordination_state_path=str(state_path),
    )
    snap = restored.snapshot()
    hardening_snap = dict(snap["membership_hardening"])
    assert int(hardening_snap["dropped_inactive_validator_total"]) == 1
    coordination = dict(snap["validator_coordination_state"])
    assert bool(coordination["enabled"]) is True
    assert str(coordination["mode"]) == "single_file"
    assert str(coordination["state_path"]) == str(state_path)
    assert bool(coordination["read_quorum_reached"]) is True
    assert int(coordination["generation"]) >= 1


def test_quorum_runtime_replicated_validator_coordination_reports_read_quorum_failure(tmp_path):
    replicas = [
        tmp_path / "coord_a.json",
        tmp_path / "coord_b.json",
        tmp_path / "coord_c.json",
    ]
    runtime = FabricQuorumRuntimeService.from_policy_settings(
        required_proof_accepts=1,
        required_trust_accepts=1,
        required_validator_ids=["validator-1"],
        validator_coordination_replica_paths=[str(path) for path in replicas],
        validator_coordination_replica_read_quorum=2,
        validator_coordination_replica_write_quorum=2,
    )
    runtime.register_commit("node-A:coord:replicated")
    for path in replicas[1:]:
        path.unlink()

    restored = FabricQuorumRuntimeService.from_policy_settings(
        required_proof_accepts=1,
        required_trust_accepts=1,
        required_validator_ids=["validator-1"],
        validator_coordination_replica_paths=[str(path) for path in replicas],
        validator_coordination_replica_read_quorum=2,
        validator_coordination_replica_write_quorum=2,
    )
    coordination = dict(restored.snapshot()["validator_coordination_state"])
    assert bool(coordination["enabled"]) is True
    assert str(coordination["mode"]) == "replicated"
    assert list(coordination["replica_paths"]) == [str(path) for path in replicas]
    assert int(coordination["read_quorum"]) == 2
    assert int(coordination["write_quorum"]) == 2
    assert bool(coordination["read_quorum_reached"]) is False
    assert "read quorum not reached" in str(coordination["last_sync_error"])


def test_quorum_runtime_ignores_validator_coordination_state_on_validator_set_mismatch(tmp_path):
    state_path = tmp_path / "validator_coordination_state.json"
    state_path.write_text(
        json.dumps(
            {
                "schema_version": "detm.fabric.validator_coordination_state.v1",
                "generation": 7,
                "updated_at_ms": 123456,
                "required_validator_ids": ["validator-other"],
                "membership_hardening_counts": {
                    "dropped_inactive_validator_total": 9,
                    "dropped_sender_mismatch_total": 3,
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    runtime = FabricQuorumRuntimeService.from_policy_settings(
        required_proof_accepts=1,
        required_trust_accepts=1,
        required_validator_ids=["validator-1"],
        validator_coordination_state_path=str(state_path),
    )
    snap = runtime.snapshot()
    hardening = dict(snap["membership_hardening"])
    assert int(hardening["dropped_inactive_validator_total"]) == 0
    assert int(hardening["dropped_sender_mismatch_total"]) == 0
    coordination = dict(snap["validator_coordination_state"])
    assert "validator-set mismatch" in str(coordination["last_sync_error"])

