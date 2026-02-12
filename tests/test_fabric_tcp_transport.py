from __future__ import annotations

import time

from detm.runtime.commit_packet import CommitPacket
from detm.runtime.fabric_artifact_store import FileFabricArtifactStore
from detm.runtime.fabric_epoch import FileEpochWatermarkCoordinator
from detm.runtime.fabric_handshake import FabricHandshakeService
from detm.runtime.fabric_quorum import InMemoryQuorumCoordinator, ValidatorSetQuorumPolicy
from detm.runtime.fabric_validator import LocalFabricValidator
from detm.runtime.fabric_envelope import FabricEnvelope
from detm.runtime.fabric_tcp_transport import TcpFabricRelay, TcpFabricTransport, open_fabric_transport
from detm.runtime.fabric_transport import InMemoryFabricBus


def _wait_until(predicate, timeout_s: float = 2.0) -> bool:
    started = time.perf_counter()
    while (time.perf_counter() - started) < timeout_s:
        if bool(predicate()):
            return True
        time.sleep(0.01)
    return False


def test_open_fabric_transport_memory_returns_in_memory_adapter():
    adapter = open_fabric_transport(transport="memory")
    try:
        assert isinstance(adapter, InMemoryFabricBus)
    finally:
        adapter.close()


def test_tcp_fabric_transport_roundtrip_between_two_clients():
    relay = TcpFabricRelay(host="127.0.0.1", port=0)
    relay.start()
    host, port = relay.address
    sender = TcpFabricTransport.connect(host=host, port=port)
    receiver = TcpFabricTransport.connect(host=host, port=port)
    received: list[FabricEnvelope] = []

    try:
        receiver.subscribe("fabric.commit", lambda env: received.append(env), mode="realtime")
        sender.publish(
            FabricEnvelope.from_dict(
                {
                    "message_type": "commit",
                    "channel": "fabric.commit",
                    "mode": "realtime",
                    "sender": "node-A",
                    "payload_ref": "artifact://commit/node-A/1",
                    "commit_ref": "node-A:1",
                }
            )
        )

        assert _wait_until(lambda: len(received) >= 1)
        assert received[0].message_type == "commit"
        assert received[0].commit_ref == "node-A:1"
    finally:
        sender.close()
        receiver.close()
        relay.stop()


def test_tcp_fabric_transport_distributed_quorum_with_inline_payload_bridge():
    relay = TcpFabricRelay(host="127.0.0.1", port=0)
    relay.start()
    host, port = relay.address

    node = TcpFabricTransport.connect(host=host, port=port)
    validator1 = TcpFabricTransport.connect(host=host, port=port)
    validator2 = TcpFabricTransport.connect(host=host, port=port)
    collector = TcpFabricTransport.connect(host=host, port=port)

    ack_store_1: dict[str, object] = {}
    ack_store_2: dict[str, object] = {}

    def _resolve_missing(_payload_ref: str) -> CommitPacket | None:
        return None

    def _write_ack_1(ack):
        ref = f"artifact://ack/v1/{len(ack_store_1) + 1}"
        ack_store_1[ref] = ack
        return ref

    def _write_ack_2(ack):
        ref = f"artifact://ack/v2/{len(ack_store_2) + 1}"
        ack_store_2[ref] = ack
        return ref

    service_1 = FabricHandshakeService(
        transport=validator1,
        validator=LocalFabricValidator(validator_id="validator-1"),
        commit_resolver=_resolve_missing,
        ack_writer=_write_ack_1,
    )
    service_2 = FabricHandshakeService(
        transport=validator2,
        validator=LocalFabricValidator(validator_id="validator-2"),
        commit_resolver=_resolve_missing,
        ack_writer=_write_ack_2,
    )
    service_1.start()
    service_2.start()

    policy = ValidatorSetQuorumPolicy(
        required_proof_accepts=2,
        required_trust_accepts=2,
        required_unique_proof_validators=2,
        required_unique_trust_validators=2,
        required_validator_ids=frozenset({"validator-1", "validator-2"}),
        enforce_required_validator_ids=True,
    )
    coordinator = InMemoryQuorumCoordinator(policy=policy, ack_resolver=None)
    collector.subscribe("fabric.ack", lambda env: coordinator.on_ack_envelope(env), mode="realtime")
    try:
        commit = CommitPacket.from_dict(
            {
                "commit_type": "state",
                "mode": "realtime",
                "node_id": "node-A",
                "commit_id": "node-A:1",
                "tick_ref": {"base_level": "L0", "tick": 1},
                "delta_ref": "artifact://delta/1",
                "trace_ref": "trace://run/1",
                "signature": "sig://node-A/1",
            }
        )
        coordinator.register_commit("node-A:1")
        node.publish(
            FabricEnvelope.from_dict(
                {
                    "message_type": "commit",
                    "channel": "fabric.commit",
                    "mode": "realtime",
                    "sender": "node-A",
                    "payload_ref": "artifact://commit/missing/on/validators",
                    "payload_inline": commit.to_dict(),
                    "commit_ref": "node-A:1",
                }
            )
        )

        assert _wait_until(lambda: coordinator.evaluate("node-A:1").get("status") == "accepted")
    finally:
        service_1.stop()
        service_2.stop()
        node.close()
        validator1.close()
        validator2.close()
        collector.close()
        relay.stop()


def test_tcp_fabric_transport_distributed_quorum_with_shared_artifact_store(tmp_path):
    relay = TcpFabricRelay(host="127.0.0.1", port=0)
    relay.start()
    host, port = relay.address

    node = TcpFabricTransport.connect(host=host, port=port)
    validator1 = TcpFabricTransport.connect(host=host, port=port)
    validator2 = TcpFabricTransport.connect(host=host, port=port)
    collector = TcpFabricTransport.connect(host=host, port=port)
    store = FileFabricArtifactStore(tmp_path / "shared")

    service_1 = FabricHandshakeService(
        transport=validator1,
        validator=LocalFabricValidator(validator_id="validator-1"),
        commit_resolver=store.read_commit,
        ack_writer=store.write_ack,
    )
    service_2 = FabricHandshakeService(
        transport=validator2,
        validator=LocalFabricValidator(validator_id="validator-2"),
        commit_resolver=store.read_commit,
        ack_writer=store.write_ack,
    )
    service_1.start()
    service_2.start()

    policy = ValidatorSetQuorumPolicy(
        required_proof_accepts=2,
        required_trust_accepts=2,
        required_unique_proof_validators=2,
        required_unique_trust_validators=2,
        required_validator_ids=frozenset({"validator-1", "validator-2"}),
        enforce_required_validator_ids=True,
    )
    coordinator = InMemoryQuorumCoordinator(policy=policy, ack_resolver=store.read_ack)
    collector.subscribe("fabric.ack", lambda env: coordinator.on_ack_envelope(env), mode="realtime")
    try:
        commit = CommitPacket.from_dict(
            {
                "commit_type": "state",
                "mode": "realtime",
                "node_id": "node-A",
                "commit_id": "node-A:2",
                "tick_ref": {"base_level": "L0", "tick": 2},
                "delta_ref": "artifact://delta/2",
                "trace_ref": "trace://run/2",
                "signature": "sig://node-A/2",
            }
        )
        commit_ref = store.write_commit(commit, artifact_ref="artifact://commit/shared/node-A:2")
        coordinator.register_commit("node-A:2")
        node.publish(
            FabricEnvelope.from_dict(
                {
                    "message_type": "commit",
                    "channel": "fabric.commit",
                    "mode": "realtime",
                    "sender": "node-A",
                    "payload_ref": commit_ref,
                    "commit_ref": "node-A:2",
                }
            )
        )

        assert _wait_until(lambda: coordinator.evaluate("node-A:2").get("status") == "accepted")
    finally:
        service_1.stop()
        service_2.stop()
        node.close()
        validator1.close()
        validator2.close()
        collector.close()
        relay.stop()


def test_tcp_fabric_transport_distributed_epoch_regression_rejected_with_shared_state(tmp_path):
    relay = TcpFabricRelay(host="127.0.0.1", port=0)
    relay.start()
    host, port = relay.address

    node = TcpFabricTransport.connect(host=host, port=port)
    validator1 = TcpFabricTransport.connect(host=host, port=port)
    validator2 = TcpFabricTransport.connect(host=host, port=port)
    collector = TcpFabricTransport.connect(host=host, port=port)
    store = FileFabricArtifactStore(tmp_path / "shared")
    epoch_state = tmp_path / "shared" / "epoch_state.json"

    service_1 = FabricHandshakeService(
        transport=validator1,
        validator=LocalFabricValidator(validator_id="validator-1"),
        commit_resolver=store.read_commit,
        ack_writer=store.write_ack,
        epoch_coordinator=FileEpochWatermarkCoordinator(epoch_state),
    )
    service_2 = FabricHandshakeService(
        transport=validator2,
        validator=LocalFabricValidator(validator_id="validator-2"),
        commit_resolver=store.read_commit,
        ack_writer=store.write_ack,
        epoch_coordinator=FileEpochWatermarkCoordinator(epoch_state),
    )
    service_1.start()
    service_2.start()

    ack_rows: list[dict[str, object]] = []
    collector.subscribe(
        "fabric.ack",
        lambda env: ack_rows.append(dict(env.payload_inline or {})),
        mode="realtime",
    )

    try:
        c1 = CommitPacket.from_dict(
            {
                "commit_type": "state",
                "mode": "realtime",
                "node_id": "node-A",
                "commit_id": "node-A:10",
                "tick_ref": {"base_level": "L0", "tick": 10},
                "delta_ref": "artifact://delta/10",
                "trace_ref": "trace://run/10",
                "summary": {"epoch": 10, "watermark": 10},
                "signature": "sig://node-A/10",
            }
        )
        c2 = CommitPacket.from_dict(
            {
                "commit_type": "state",
                "mode": "realtime",
                "node_id": "node-A",
                "commit_id": "node-A:11",
                "parent_ref": "node-A:10",
                "tick_ref": {"base_level": "L0", "tick": 11},
                "delta_ref": "artifact://delta/11",
                "trace_ref": "trace://run/11",
                "summary": {"epoch": 9, "watermark": 9},
                "signature": "sig://node-A/11",
            }
        )
        r1 = store.write_commit(c1, artifact_ref="artifact://commit/shared/node-A:10")
        r2 = store.write_commit(c2, artifact_ref="artifact://commit/shared/node-A:11")

        node.publish(
            FabricEnvelope.from_dict(
                {
                    "message_type": "commit",
                    "channel": "fabric.commit",
                    "mode": "realtime",
                    "sender": "node-A",
                    "payload_ref": r1,
                    "commit_ref": "node-A:10",
                }
            )
        )
        node.publish(
            FabricEnvelope.from_dict(
                {
                    "message_type": "commit",
                    "channel": "fabric.commit",
                    "mode": "realtime",
                    "sender": "node-A",
                    "payload_ref": r2,
                    "commit_ref": "node-A:11",
                }
            )
        )

        assert _wait_until(lambda: len(ack_rows) >= 8)
        second_commit_rows = [row for row in ack_rows if str(row.get("commit_ref")) == "node-A:11"]
        assert len(second_commit_rows) == 4
        assert {str(row.get("status")) for row in second_commit_rows} == {"rejected"}
        assert any("epoch regression" in str(row.get("reason")) for row in second_commit_rows)
    finally:
        service_1.stop()
        service_2.stop()
        node.close()
        validator1.close()
        validator2.close()
        collector.close()
        relay.stop()
