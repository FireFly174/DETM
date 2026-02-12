from __future__ import annotations

import json

from detm.runtime.fabric_ack import ProofAck, TrustAck
from detm.runtime.fabric_envelope import FabricEnvelope
from detm.runtime.fabric_quorum_report import FabricQuorumReportBuilder
from detm.runtime.fabric_report_writer import FabricRuntimeReportWriter


class _Service:
    def __init__(self, rows: list[dict[str, str]]) -> None:
        self.dead_letters = list(rows)


class _QuorumRuntime:
    def snapshot(self) -> dict[str, object]:
        return {
            "accepted_count": 1,
            "pending_count": 0,
            "rejected_count": 0,
            "validator_registry": {"validators": []},
            "pending_timeout_ms": None,
        }


def test_fabric_report_writer_writes_expected_files(tmp_path):
    proof = ProofAck(
        validator_id="validator-1",
        node_id="node-A",
        commit_ref="node-A:1",
        status="accepted",
        signature="sig://validator-1/proof/node-A:1",
    )
    trust = TrustAck(
        validator_id="validator-1",
        node_id="node-A",
        commit_ref="node-A:1",
        status="accepted",
        signature="sig://validator-1/trust/node-A:1",
    )
    ack_env = FabricEnvelope.from_dict(
        {
            "message_type": "proof_ack",
            "channel": "fabric.ack",
            "mode": "realtime",
            "sender": "validator-1",
            "payload_ref": "artifact://ack/1",
            "commit_ref": "node-A:1",
        }
    )
    delivery_env = FabricEnvelope.from_dict(
        {
            "message_type": "delivery_ack",
            "channel": "fabric.delivery.ack",
            "mode": "realtime",
            "sender": "validator-1",
            "payload_ref": "artifact://delivery_ack/1",
            "payload_inline": {"delivery_id": "d1", "status": "received"},
            "delivery_id": "d1",
            "commit_ref": "node-A:1",
        }
    )

    quorum_builder = FabricQuorumReportBuilder(quorum_runtime=_QuorumRuntime())  # type: ignore[arg-type]
    writer = FabricRuntimeReportWriter(
        out_dir=tmp_path,
        ack_store={"a1": proof, "a2": trust},
        ack_envelopes=[ack_env],
        delivery_ack_envelopes=[delivery_env],
        quorum_report_builder=quorum_builder,
        service=_Service([{"message_type": "proof_ack", "error": "transport failed"}]),  # type: ignore[arg-type]
        commit_dead_letters=[{"message_type": "commit", "error": "publish failed"}],
    )

    writer.write_all(replay_sample_stride=1, replay_checks_total=5, replay_checks_failed=1)

    acks = [json.loads(line) for line in (tmp_path / "fabric_acks.jsonl").read_text(encoding="utf-8").splitlines()]
    ack_envs = [
        json.loads(line) for line in (tmp_path / "fabric_ack_envelopes.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    delivery_envs = [
        json.loads(line)
        for line in (tmp_path / "fabric_delivery_acks.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    report = json.loads((tmp_path / "fabric_quorum_report.json").read_text(encoding="utf-8"))
    dead_letters = json.loads((tmp_path / "fabric_dead_letters.json").read_text(encoding="utf-8"))

    assert len(acks) == 2
    assert len(ack_envs) == 1
    assert len(delivery_envs) == 1
    assert int(report["accepted_count"]) == 1
    assert dict(report["replay_sampling"]) == {
        "enabled": True,
        "sample_stride": 1,
        "checks_total": 5,
        "checks_failed": 1,
    }
    assert len(dead_letters) == 2
    assert {str(row["message_type"]) for row in dead_letters} == {"proof_ack", "commit"}


def test_fabric_report_writer_handles_empty_components(tmp_path):
    writer = FabricRuntimeReportWriter(out_dir=tmp_path)
    writer.write_all(replay_sample_stride=0, replay_checks_total=0, replay_checks_failed=0)

    assert (tmp_path / "fabric_acks.jsonl").exists()
    assert (tmp_path / "fabric_ack_envelopes.jsonl").exists()
    assert (tmp_path / "fabric_delivery_acks.jsonl").exists()
    report = json.loads((tmp_path / "fabric_quorum_report.json").read_text(encoding="utf-8"))
    assert report == {}
    dead_letters = json.loads((tmp_path / "fabric_dead_letters.json").read_text(encoding="utf-8"))
    assert dead_letters == []


def test_fabric_report_writer_applies_storage_limits(tmp_path):
    ack_store = {
        f"a{i}": ProofAck(
            validator_id="validator-1",
            node_id="node-A",
            commit_ref=f"node-A:{i}",
            status="accepted",
            signature=f"sig://validator-1/proof/node-A:{i}",
        )
        for i in range(1, 6)
    }
    ack_envelopes = [
        FabricEnvelope.from_dict(
            {
                "message_type": "proof_ack",
                "channel": "fabric.ack",
                "mode": "realtime",
                "sender": "validator-1",
                "payload_ref": f"artifact://ack/{i}",
                "commit_ref": f"node-A:{i}",
            }
        )
        for i in range(1, 6)
    ]
    delivery_ack_envelopes = [
        FabricEnvelope.from_dict(
            {
                "message_type": "delivery_ack",
                "channel": "fabric.delivery.ack",
                "mode": "realtime",
                "sender": "validator-1",
                "payload_ref": f"artifact://delivery_ack/{i}",
                "payload_inline": {"delivery_id": f"d{i}", "status": "received"},
                "delivery_id": f"d{i}",
                "commit_ref": f"node-A:{i}",
            }
        )
        for i in range(1, 6)
    ]
    writer = FabricRuntimeReportWriter(
        out_dir=tmp_path,
        ack_store=ack_store,
        ack_envelopes=ack_envelopes,
        delivery_ack_envelopes=delivery_ack_envelopes,
        service=_Service([{"message_type": f"service-{i}", "error": "transport failed"} for i in range(1, 4)]),  # type: ignore[arg-type]
        commit_dead_letters=[{"message_type": f"commit-{i}", "error": "publish failed"} for i in range(1, 4)],
        acks_retention_window=4,
        acks_compaction_budget=2,
        ack_envelopes_retention_window=3,
        ack_envelopes_compaction_budget=0,
        delivery_acks_retention_window=0,
        delivery_acks_compaction_budget=1,
        dead_letters_retention_window=5,
        dead_letters_compaction_budget=2,
    )

    writer.write_all(replay_sample_stride=0, replay_checks_total=0, replay_checks_failed=0)

    acks = [json.loads(line) for line in (tmp_path / "fabric_acks.jsonl").read_text(encoding="utf-8").splitlines() if line]
    ack_envs = [
        json.loads(line) for line in (tmp_path / "fabric_ack_envelopes.jsonl").read_text(encoding="utf-8").splitlines() if line
    ]
    delivery_envs = [
        json.loads(line)
        for line in (tmp_path / "fabric_delivery_acks.jsonl").read_text(encoding="utf-8").splitlines()
        if line
    ]
    dead_letters = json.loads((tmp_path / "fabric_dead_letters.json").read_text(encoding="utf-8"))

    assert [str(row["commit_ref"]) for row in acks] == ["node-A:4", "node-A:5"]
    assert [str(row["commit_ref"]) for row in ack_envs] == ["node-A:3", "node-A:4", "node-A:5"]
    assert [str(row["commit_ref"]) for row in delivery_envs] == ["node-A:5"]
    assert [str(row["message_type"]) for row in dead_letters] == ["commit-2", "commit-3"]
