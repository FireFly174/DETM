from __future__ import annotations

import json

from detm_app.runtime.session import DetmSession
from detm_app.runtime.subscribers import CommitJsonlWriter, CommitValidationReporter
from detm.runtime.commit_packet import CommitPacket
from detm.runtime.config import DETMConfig
from detm.runtime.fabric import validate_commit_paths
from detm.runtime.level_policy import LevelPolicy
from detm.runtime.schemas import DETM_COMMIT_PACKET_V1


def test_commit_validation_report_ok_with_watermark(tmp_path):
    cfg = DETMConfig(
        backend="numpy",
        device="cpu",
        width=6,
        height=6,
        initial_noise=0.01,
        level_policy=LevelPolicy(commit_stride=1, audit_commit_enabled=True, audit_commit_stride=3),
    )
    session = DetmSession.create(cfg, seed=9)
    CommitJsonlWriter.attach(session.bus, tmp_path / "commits.jsonl", node_id="node-v", mode="realtime")
    CommitJsonlWriter.attach(
        session.bus,
        tmp_path / "commits_audit.jsonl",
        node_id="node-v",
        commit_type="proof",
        mode="audit",
    )
    CommitValidationReporter.attach(session.bus, tmp_path)

    for _ in range(7):
        session.step(None, 1, rng=session.state.restore_rng())
    session.close()

    report = json.loads((tmp_path / "commit_validation.json").read_text(encoding="utf-8"))
    assert report["status"] == "ok"
    assert report["streams"]["realtime"]["count"] == 7
    assert report["streams"]["audit"]["count"] == 2
    assert report["watermark"]["tick"] == 6
    assert report["watermark"]["lag_realtime_vs_audit"] == 1


def test_validate_commit_paths_detects_broken_parent_chain(tmp_path):
    p1 = CommitPacket.from_dict(
        {
            "schema_version": DETM_COMMIT_PACKET_V1,
            "commit_type": "state",
            "mode": "realtime",
            "node_id": "node-x",
            "commit_id": "node-x:1",
            "parent_ref": None,
            "tick_ref": {"base_level": "L0", "tick": 1},
            "delta_ref": "delta://1",
            "trace_ref": "trace://L0/1",
            "signature": "sig://node-x/1",
        }
    )
    p2 = CommitPacket.from_dict(
        {
            "schema_version": DETM_COMMIT_PACKET_V1,
            "commit_type": "state",
            "mode": "realtime",
            "node_id": "node-x",
            "commit_id": "node-x:2",
            "parent_ref": "node-x:999",
            "tick_ref": {"base_level": "L0", "tick": 2},
            "delta_ref": "delta://2",
            "trace_ref": "trace://L0/2",
            "signature": "sig://node-x/2",
        }
    )
    (tmp_path / "commits.jsonl").write_text(
        "\n".join(
            [
                json.dumps(p1.to_dict(), ensure_ascii=False),
                json.dumps(p2.to_dict(), ensure_ascii=False),
            ]
        ),
        encoding="utf-8",
    )

    report = validate_commit_paths(
        realtime_path=tmp_path / "commits.jsonl",
        audit_path=tmp_path / "commits_audit.jsonl",
    )

    assert report["status"] == "error"
    assert any("broken parent chain" in issue for issue in report["issues"])


