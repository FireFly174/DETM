from __future__ import annotations

import hashlib
import json
import time
from unittest.mock import patch

from detm.runtime.commit_packet import CommitPacket
from detm.runtime.fabric import FileFabricArtifactStore
from detm.runtime.fabric import FileEpochWatermarkCoordinator
from detm.runtime.fabric import FabricHandshakeService
from detm.runtime.fabric import InMemoryQuorumCoordinator, ValidatorSetQuorumPolicy
from detm.runtime.fabric import LocalFabricValidator
from detm.runtime.fabric import FabricEnvelope
from detm.runtime.fabric import TcpFabricRelay, TcpFabricTransport, open_fabric_transport
from detm.runtime.fabric import InMemoryFabricBus


def _wait_until(predicate, timeout_s: float = 2.0) -> bool:
    started = time.perf_counter()
    while (time.perf_counter() - started) < timeout_s:
        if bool(predicate()):
            return True
        time.sleep(0.01)
    return False


def test_open_fabric_transport_memory_returns_in_memory_adapter():
    adapter = open_fabric_transport(
        transport="memory",
        dedup_ingress_enabled=True,
        dedup_ttl_ms=123,
        dedup_max_entries=456,
    )
    try:
        assert isinstance(adapter, InMemoryFabricBus)
        snap = adapter.snapshot()
        dedup = dict(snap.get("dedup", {}))
        assert bool(dedup.get("enabled")) is True
        assert int(dedup.get("ttl_ms", 0)) == 123
        assert int(dedup.get("max_entries", 0)) == 456
    finally:
        adapter.close()


def test_tcp_fabric_transport_requires_key_when_auth_enabled():
    relay = TcpFabricRelay(host="127.0.0.1", port=0)
    relay.start()
    host, port = relay.address
    try:
        try:
            TcpFabricTransport.connect(host=host, port=port, auth_enabled=True, auth_key=None)
        except ValueError as exc:
            assert "auth_key must be non-empty" in str(exc)
        else:  # pragma: no cover
            raise AssertionError("Expected ValueError when auth_enabled=true without auth_key")
    finally:
        relay.stop()


def test_open_fabric_transport_tcp_forwards_tls_options():
    with patch("detm.runtime.fabric.tcp_transport.factory.TcpFabricTransport.connect") as connect_mock:
        connect_mock.return_value = InMemoryFabricBus()
        adapter = open_fabric_transport(
            transport="tcp",
            host="127.0.0.1",
            port=32123,
            connect=True,
            tls_enabled=True,
            tls_server_hostname="node.local",
            tls_ca_file="ca.pem",
            tls_cert_file="cert.pem",
            tls_key_file="key.pem",
            tls_require_client_cert=True,
            tls_client_ca_file="client-ca.pem",
            tls_insecure_skip_verify=True,
            tls_identity_source="san",
            tls_identity_fallback_to_fingerprint=True,
        )
        try:
            assert adapter is connect_mock.return_value
            _args, kwargs = connect_mock.call_args
            assert kwargs["tls_enabled"] is True
            assert kwargs["tls_server_hostname"] == "node.local"
            assert kwargs["tls_ca_file"] == "ca.pem"
            assert kwargs["tls_cert_file"] == "cert.pem"
            assert kwargs["tls_key_file"] == "key.pem"
            assert kwargs["tls_require_client_cert"] is True
            assert kwargs["tls_client_ca_file"] == "client-ca.pem"
            assert kwargs["tls_insecure_skip_verify"] is True
            assert kwargs["tls_identity_source"] == "san"
            assert kwargs["tls_identity_fallback_to_fingerprint"] is True
        finally:
            adapter.close()


def test_tcp_fabric_transport_start_local_tls_requires_server_cert_and_key():
    try:
        TcpFabricTransport.start_local(tls_enabled=True, tls_insecure_skip_verify=True)
    except ValueError as exc:
        assert "tls_cert_file and tls_key_file are required" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected ValueError when tls_enabled=true without tls cert/key")


def test_tcp_fabric_transport_start_local_tls_requires_client_ca_when_client_cert_required():
    try:
        TcpFabricTransport.start_local(
            tls_enabled=True,
            tls_cert_file="cert.pem",
            tls_key_file="key.pem",
            tls_require_client_cert=True,
        )
    except ValueError as exc:
        assert "tls_client_ca_file is required" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected ValueError when tls_require_client_cert=true without tls_client_ca_file")


def test_tcp_fabric_relay_inject_transport_identity_overwrites_payload_field():
    raw = b'{"message_type":"proof_ack","channel":"fabric.ack","mode":"realtime","sender":"validator-1","payload_ref":"artifact://ack/1","transport_identity":"spoofed"}'
    out = TcpFabricRelay._inject_transport_identity(raw, "cn:validator-1")
    env = FabricEnvelope.from_dict(json.loads(out.decode("utf-8")))
    assert env.transport_identity == "cn:validator-1"


def test_tcp_fabric_relay_select_transport_identity_auto_prefers_cn_then_san_then_fingerprint():
    cert = {
        "subject": ((("commonName", "validator-1"),),),
        "subjectAltName": (("DNS", "validator-1.local"),),
    }
    out = TcpFabricRelay._select_transport_identity(
        cert=cert,
        cert_bin=b"cert-binary",
        source="auto",
        allow_fingerprint_fallback=False,
    )
    assert out == "cn:validator-1"


def test_tcp_fabric_relay_select_transport_identity_cn_with_optional_fingerprint_fallback():
    cert = {
        "subject": (),
        "subjectAltName": (("DNS", "validator-1.local"),),
    }
    fingerprint = "sha256:" + hashlib.sha256(b"cert-binary").hexdigest()

    out_without_fallback = TcpFabricRelay._select_transport_identity(
        cert=cert,
        cert_bin=b"cert-binary",
        source="cn",
        allow_fingerprint_fallback=False,
    )
    out_with_fallback = TcpFabricRelay._select_transport_identity(
        cert=cert,
        cert_bin=b"cert-binary",
        source="cn",
        allow_fingerprint_fallback=True,
    )
    assert out_without_fallback is None
    assert out_with_fallback == fingerprint


def test_tcp_fabric_relay_select_transport_identity_san_and_fingerprint_modes():
    cert = {
        "subject": (),
        "subjectAltName": (("DNS", "validator-1.local"),),
    }
    fingerprint = "sha256:" + hashlib.sha256(b"cert-binary").hexdigest()

    out_san = TcpFabricRelay._select_transport_identity(
        cert=cert,
        cert_bin=b"cert-binary",
        source="san",
        allow_fingerprint_fallback=False,
    )
    out_fingerprint = TcpFabricRelay._select_transport_identity(
        cert=cert,
        cert_bin=b"cert-binary",
        source="fingerprint",
        allow_fingerprint_fallback=False,
    )
    assert out_san == "dns:validator-1.local"
    assert out_fingerprint == fingerprint


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


def test_tcp_fabric_transport_dedup_ingress_drops_duplicate_delivery_id():
    relay = TcpFabricRelay(host="127.0.0.1", port=0)
    relay.start()
    host, port = relay.address
    sender = TcpFabricTransport.connect(host=host, port=port)
    receiver = TcpFabricTransport.connect(
        host=host,
        port=port,
        dedup_ingress_enabled=True,
        dedup_ttl_ms=60_000,
        dedup_max_entries=256,
    )
    received: list[FabricEnvelope] = []

    try:
        receiver.subscribe("fabric.commit", lambda env: received.append(env), mode="realtime")
        env = FabricEnvelope.from_dict(
            {
                "message_type": "commit",
                "channel": "fabric.commit",
                "mode": "realtime",
                "sender": "node-A",
                "payload_ref": "artifact://commit/node-A/dup",
                "commit_ref": "node-A:dup",
                "delivery_id": "node-A:dup:1",
            }
        )
        sender.publish(env)
        sender.publish(env)

        assert _wait_until(lambda: len(received) >= 1)
        time.sleep(0.05)
        assert len(received) == 1
        snap = receiver.snapshot()
        dedup = dict(snap.get("dedup", {}))
        assert bool(dedup.get("enabled")) is True
        assert int(dedup.get("duplicates_total", 0)) >= 1
    finally:
        sender.close()
        receiver.close()
        relay.stop()


def test_tcp_fabric_transport_auth_accepts_with_matching_key():
    relay = TcpFabricRelay(host="127.0.0.1", port=0)
    relay.start()
    host, port = relay.address
    sender = TcpFabricTransport.connect(
        host=host,
        port=port,
        auth_enabled=True,
        auth_key="shared-secret",
        auth_key_id="node-key",
    )
    receiver = TcpFabricTransport.connect(
        host=host,
        port=port,
        auth_enabled=True,
        auth_key="shared-secret",
        auth_key_id="node-key",
    )
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
                    "payload_ref": "artifact://commit/node-A/auth-1",
                    "commit_ref": "node-A:auth-1",
                }
            )
        )
        assert _wait_until(lambda: len(received) >= 1)
        assert str(received[0].auth_key_id) == "node-key"
        snap = receiver.snapshot()
        auth = dict(snap.get("auth", {}))
        assert bool(auth.get("enabled")) is True
        assert int(auth.get("verified_total", 0)) >= 1
        assert int(auth.get("rejected_total", 0)) == 0
    finally:
        sender.close()
        receiver.close()
        relay.stop()


def test_tcp_fabric_transport_auth_rejects_with_mismatched_key():
    relay = TcpFabricRelay(host="127.0.0.1", port=0)
    relay.start()
    host, port = relay.address
    sender = TcpFabricTransport.connect(
        host=host,
        port=port,
        auth_enabled=True,
        auth_key="sender-secret",
        auth_key_id="node-key",
    )
    receiver = TcpFabricTransport.connect(
        host=host,
        port=port,
        auth_enabled=True,
        auth_key="receiver-secret",
        auth_key_id="node-key",
    )
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
                    "payload_ref": "artifact://commit/node-A/auth-bad",
                    "commit_ref": "node-A:auth-bad",
                }
            )
        )
        time.sleep(0.05)
        assert len(received) == 0
        snap = receiver.snapshot()
        auth = dict(snap.get("auth", {}))
        assert bool(auth.get("enabled")) is True
        assert int(auth.get("rejected_total", 0)) >= 1
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


