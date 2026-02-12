from __future__ import annotations

from detm.runtime.fabric_runtime_bundle import FabricHandshakeRuntimeBundle


class _Service:
    def __init__(self) -> None:
        self.started = 0
        self.stopped = 0

    def start(self) -> None:
        self.started += 1

    def stop(self) -> None:
        self.stopped += 1


class _AckRuntime:
    def __init__(self) -> None:
        self.started = 0
        self.stopped = 0
        self.subscriptions = [("fabric.ack.realtime", "realtime")]

    def start(self) -> None:
        self.started += 1

    def stop(self) -> None:
        self.stopped += 1


class _DeliveryRuntime:
    def __init__(self) -> None:
        self.started = 0
        self.stopped = 0
        self.subscriptions = [("fabric.delivery.ack.realtime", "realtime")]

    def start(self) -> None:
        self.started += 1

    def stop(self) -> None:
        self.stopped += 1


class _Transport:
    def __init__(self) -> None:
        self.closed = 0

    def close(self) -> None:
        self.closed += 1


class _EpochConsensus:
    def __init__(self) -> None:
        self.stopped = 0

    def stop(self) -> None:
        self.stopped += 1


def test_runtime_bundle_start_starts_all_runtimes():
    service = _Service()
    ack_runtime = _AckRuntime()
    delivery_runtime = _DeliveryRuntime()
    transport = _Transport()
    epoch = _EpochConsensus()
    bundle = FabricHandshakeRuntimeBundle(
        service=service,  # type: ignore[arg-type]
        ack_runtime=ack_runtime,  # type: ignore[arg-type]
        delivery_runtime=delivery_runtime,  # type: ignore[arg-type]
        transport=transport,  # type: ignore[arg-type]
        epoch_consensus=epoch,  # type: ignore[arg-type]
    )

    bundle.start()

    assert service.started == 1
    assert ack_runtime.started == 1
    assert delivery_runtime.started == 1
    assert bundle.ack_subscriptions() == [("fabric.ack.realtime", "realtime")]
    assert bundle.delivery_ack_subscriptions() == [("fabric.delivery.ack.realtime", "realtime")]


def test_runtime_bundle_stop_stops_all_and_closes_transport():
    service = _Service()
    ack_runtime = _AckRuntime()
    delivery_runtime = _DeliveryRuntime()
    transport = _Transport()
    epoch = _EpochConsensus()
    bundle = FabricHandshakeRuntimeBundle(
        service=service,  # type: ignore[arg-type]
        ack_runtime=ack_runtime,  # type: ignore[arg-type]
        delivery_runtime=delivery_runtime,  # type: ignore[arg-type]
        transport=transport,  # type: ignore[arg-type]
        epoch_consensus=epoch,  # type: ignore[arg-type]
    )

    bundle.stop()

    assert service.stopped == 1
    assert ack_runtime.stopped == 1
    assert delivery_runtime.stopped == 1
    assert transport.closed == 1
    assert epoch.stopped == 1
