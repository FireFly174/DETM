from __future__ import annotations

from detm.runtime.fabric_ack import ProofAck, TrustAck
from detm.runtime.fabric_envelope import FabricEnvelope
from detm.runtime.fabric_quorum_runtime import FabricQuorumRuntimeService


def _proof_env(commit_ref: str, validator_id: str) -> FabricEnvelope:
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
        }
    )


def _trust_env(commit_ref: str, validator_id: str) -> FabricEnvelope:
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
