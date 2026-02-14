from __future__ import annotations

from detm.runtime.fabric import channel_for_mode, mode_channels, start_runtime_bundle


class _Bundle:
    def __init__(self) -> None:
        self.started = 0

    def start(self) -> None:
        self.started += 1

    def ack_subscriptions(self):
        return [("fabric.ack.realtime", "realtime")]

    def delivery_ack_subscriptions(self):
        return [("fabric.delivery.ack.realtime", "realtime")]


def test_mode_channels_returns_mapping_only_when_enabled():
    assert mode_channels(False, "fabric.ack") is None
    assert mode_channels(True, " ") is None
    assert mode_channels(True, "fabric.ack") == {
        "realtime": "fabric.ack.realtime",
        "audit": "fabric.ack.audit",
    }


def test_channel_for_mode_uses_mapping_and_fallback():
    mapping = {"realtime": "fabric.ack.realtime", "audit": "fabric.ack.audit"}
    assert channel_for_mode(base_channel="fabric.ack", mode="realtime", mapping=mapping) == "fabric.ack.realtime"
    assert channel_for_mode(base_channel="fabric.ack", mode="unknown", mapping=mapping) == "fabric.ack"
    assert channel_for_mode(base_channel="fabric.ack", mode="audit", mapping=None) == "fabric.ack"


def test_start_runtime_bundle_returns_subscriptions():
    ack, delivery = start_runtime_bundle(None)
    assert ack == []
    assert delivery == []

    bundle = _Bundle()
    ack, delivery = start_runtime_bundle(bundle)  # type: ignore[arg-type]
    assert bundle.started == 1
    assert ack == [("fabric.ack.realtime", "realtime")]
    assert delivery == [("fabric.delivery.ack.realtime", "realtime")]

