from __future__ import annotations

import numpy as np
import sys
import types

from detm.runtime import api
from detm.runtime.config import DETMConfig
from detm_app.transport.client import VizClient
from detm_app.transport.daemon import VizHub
from detm_app.ui.napari.subscriber import (
    _format_status_text,
    _patch_six_meta_path_importer,
    _LayerPresenter,
    NapariFrame,
    packet_to_layer_frame,
    resolve_napari_endpoint,
    run_napari_subscriber,
    wait_latest_packet,
)
from detm_app.transport.subscriber import TcpVizSubscriber, VizPacket
from detm_app.transport import (
    clear_viz_endpoint_registry,
    load_viz_endpoint_registry,
    open_viz_transport,
    write_viz_endpoint_registry,
)


def test_packet_to_layer_frame_decodes_runtime_state_blob():
    config = DETMConfig(width=8, height=6, backend="numpy")
    state = api.reset(config, seed=7)
    state, obs = api.step(state, influence=None, n_ticks=3)
    blob = api.serialize(state)

    frame = packet_to_layer_frame(
        VizPacket(tick=int(state.step_count), state_blob=blob, signature=list(obs.signature.vector))
    )

    assert frame.tick == int(state.step_count)
    assert sorted(frame.layers.keys()) == ["energy", "entropy", "internal_time"]
    assert frame.signature == [float(x) for x in list(obs.signature.vector)]
    assert frame.active_level is None
    assert frame.meta == {}
    for arr in frame.layers.values():
        assert arr.shape == (int(config.height), int(config.width))


def test_patch_six_meta_path_importer_sets_missing_path():
    import sys
    import six  # noqa: F401

    _patch_six_meta_path_importer()
    for importer in list(sys.meta_path):
        if type(importer).__name__ == "_SixMetaPathImporter":
            assert hasattr(importer, "_path")


def test_tcp_subscriber_roundtrip_decodes_canonical_frame():
    config = DETMConfig(width=10, height=5, backend="numpy")
    state = api.reset(config, seed=13)
    state, obs = api.step(state, influence=None, n_ticks=2)
    blob = api.serialize(state)

    hub = VizHub(host="127.0.0.1", port=0)
    hub.start()
    host, port = hub.address
    subscriber = TcpVizSubscriber(host=host, port=port)
    client = VizClient(host=host, port=port)

    try:
        client.send_state(
            state_blob=blob,
            tick=int(state.step_count),
            signature=list(obs.signature.vector),
            meta={"active_level": "L1", "source": "test"},
        )
        pkt = wait_latest_packet(subscriber, timeout_s=2.0)
        assert pkt is not None

        frame = packet_to_layer_frame(pkt)
        assert frame.tick == int(state.step_count)
        assert frame.signature == [float(x) for x in list(obs.signature.vector)]
        assert frame.active_level == "L1"
        assert frame.meta.get("source") == "test"
        assert frame.layers["energy"].shape == (int(config.height), int(config.width))
    finally:
        client.close()
        subscriber.close()
        hub.stop()


def test_resolve_napari_endpoint_uses_env(monkeypatch):
    monkeypatch.setenv("DETM_VIZ_PORT", "6677")
    monkeypatch.setenv("DETM_VIZ_HOST", "127.0.0.9")
    host, port, source = resolve_napari_endpoint(host=None, port=None)
    assert source == "env"
    assert host == "127.0.0.9"
    assert port == 6677


def test_resolve_napari_endpoint_uses_registry(tmp_path, monkeypatch):
    endpoint_path = tmp_path / "viz_endpoint.json"
    monkeypatch.setenv("DETM_VIZ_ENDPOINT_PATH", str(endpoint_path))
    monkeypatch.delenv("DETM_VIZ_PORT", raising=False)
    monkeypatch.delenv("DETM_VIZ_HOST", raising=False)

    write_viz_endpoint_registry(host="127.0.0.3", port=7788)
    loaded = load_viz_endpoint_registry()
    assert loaded == ("127.0.0.3", 7788)

    host, port, source = resolve_napari_endpoint(host=None, port=None)
    assert source == "registry"
    assert host == "127.0.0.3"
    assert port == 7788


def test_clear_viz_endpoint_registry_clears_only_matching_entry(tmp_path, monkeypatch):
    endpoint_path = tmp_path / "viz_endpoint.json"
    monkeypatch.setenv("DETM_VIZ_ENDPOINT_PATH", str(endpoint_path))

    write_viz_endpoint_registry(host="127.0.0.7", port=9001)
    assert load_viz_endpoint_registry() == ("127.0.0.7", 9001)

    clear_viz_endpoint_registry(host="127.0.0.8", port=9001)
    assert load_viz_endpoint_registry() == ("127.0.0.7", 9001)

    clear_viz_endpoint_registry(host="127.0.0.7", port=9001)
    assert load_viz_endpoint_registry() is None


def test_open_viz_transport_close_clears_registry_for_local_daemon(tmp_path, monkeypatch):
    endpoint_path = tmp_path / "viz_endpoint.json"
    monkeypatch.setenv("DETM_VIZ_ENDPOINT_PATH", str(endpoint_path))

    transport = open_viz_transport(
        enabled=True,
        transport="tcp",
        host="127.0.0.1",
        port=0,
        connect=False,
        keep_open=False,
    )
    assert load_viz_endpoint_registry() is not None
    transport.close()
    assert load_viz_endpoint_registry() is None


def test_resolve_napari_endpoint_cli_overrides_env_and_registry(tmp_path, monkeypatch):
    endpoint_path = tmp_path / "viz_endpoint.json"
    monkeypatch.setenv("DETM_VIZ_ENDPOINT_PATH", str(endpoint_path))
    monkeypatch.setenv("DETM_VIZ_PORT", "5555")
    monkeypatch.setenv("DETM_VIZ_HOST", "127.0.0.5")
    write_viz_endpoint_registry(host="127.0.0.7", port=7777)

    host, port, source = resolve_napari_endpoint(host="127.0.0.4", port=6666)
    assert source == "cli"
    assert host == "127.0.0.4"
    assert port == 6666


def test_resolve_napari_endpoint_env_host_is_overridable(monkeypatch):
    monkeypatch.setenv("DETM_VIZ_PORT", "6677")
    monkeypatch.setenv("DETM_VIZ_HOST", "127.0.0.9")

    host, port, source = resolve_napari_endpoint(host="127.0.0.8", port=None)
    assert source == "env"
    assert host == "127.0.0.8"
    assert port == 6677


def test_resolve_napari_endpoint_registry_host_is_overridable(tmp_path, monkeypatch):
    endpoint_path = tmp_path / "viz_endpoint.json"
    monkeypatch.setenv("DETM_VIZ_ENDPOINT_PATH", str(endpoint_path))
    monkeypatch.delenv("DETM_VIZ_PORT", raising=False)
    monkeypatch.delenv("DETM_VIZ_HOST", raising=False)
    write_viz_endpoint_registry(host="127.0.0.3", port=7788)

    host, port, source = resolve_napari_endpoint(host="127.0.0.2", port=None)
    assert source == "registry"
    assert host == "127.0.0.2"
    assert port == 7788


def test_resolve_napari_endpoint_invalid_env_port_raises(monkeypatch):
    monkeypatch.setenv("DETM_VIZ_PORT", "0")
    monkeypatch.delenv("DETM_VIZ_HOST", raising=False)

    try:
        resolve_napari_endpoint(host=None, port=None)
    except ValueError as exc:
        assert "DETM_VIZ_PORT must be > 0" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected ValueError for invalid DETM_VIZ_PORT")


def test_resolve_napari_endpoint_without_sources_raises_system_exit(tmp_path, monkeypatch):
    endpoint_path = tmp_path / "viz_endpoint.json"
    monkeypatch.setenv("DETM_VIZ_ENDPOINT_PATH", str(endpoint_path))
    monkeypatch.delenv("DETM_VIZ_PORT", raising=False)
    monkeypatch.delenv("DETM_VIZ_HOST", raising=False)

    try:
        resolve_napari_endpoint(host=None, port=None)
    except SystemExit as exc:
        msg = str(exc)
        assert "Cannot resolve viz endpoint." in msg
        assert "detm_napari_viewer.py --port" in msg
    else:  # pragma: no cover
        raise AssertionError("Expected SystemExit when endpoint cannot be resolved")


class _PollingStub:
    def __init__(self, packets):
        self._packets = list(packets)

    def poll_latest(self):
        if not self._packets:
            return None
        return self._packets.pop(0)


def test_wait_latest_packet_returns_none_on_timeout():
    pkt = wait_latest_packet(_PollingStub([]), timeout_s=0.02, poll_interval_s=0.005)
    assert pkt is None


def test_wait_latest_packet_returns_first_available_packet():
    expected = VizPacket(tick=7, state_blob=b"abc", signature=[1.0, 2.0])
    pkt = wait_latest_packet(_PollingStub([None, None, expected]), timeout_s=0.2, poll_interval_s=0.005)
    assert pkt is expected


class _FakeLayer:
    def __init__(self, data):
        self.data = np.asarray(data, dtype=np.float32)
        self.contrast_limits = None


class _FakeViewer:
    def __init__(self):
        self.layers = {}

    def add_image(self, image, name):
        layer = _FakeLayer(image)
        self.layers[name] = layer
        return layer


def test_layer_presenter_creates_and_updates_layers_with_autoscale():
    viewer = _FakeViewer()
    presenter = _LayerPresenter(viewer, autoscale=True)

    frame1 = NapariFrame(
        tick=1,
        signature=[0.1],
        active_level="L1",
        meta={"active_level": "L1"},
        layers={
            "energy": np.array([[0.0, 1.0], [2.0, 3.0]], dtype=np.float32),
            "entropy": np.array([[4.0, 5.0], [6.0, 7.0]], dtype=np.float32),
            "internal_time": np.array([[1.0, 1.0], [1.0, 1.0]], dtype=np.float32),
        },
    )
    presenter.render(frame1)
    assert sorted(viewer.layers.keys()) == ["energy", "entropy", "internal_time"]
    energy_layer = viewer.layers["energy"]
    assert tuple(energy_layer.contrast_limits) == (0.0, 3.0)
    # constant image is left unchanged by autoscale (no vmin < vmax range)
    assert viewer.layers["internal_time"].contrast_limits is None

    frame2 = NapariFrame(
        tick=2,
        signature=[0.2],
        active_level="L2",
        meta={"active_level": "L2"},
        layers={
            "energy": np.array([[10.0, 11.0], [12.0, 13.0]], dtype=np.float32),
            "entropy": np.array([[8.0, 9.0], [10.0, 11.0]], dtype=np.float32),
            "internal_time": np.array([[2.0, 3.0], [4.0, 5.0]], dtype=np.float32),
        },
    )
    presenter.render(frame2)
    assert viewer.layers["energy"] is energy_layer
    assert np.allclose(viewer.layers["energy"].data, frame2.layers["energy"])
    assert tuple(viewer.layers["energy"].contrast_limits) == (10.0, 13.0)


def test_run_napari_subscriber_rejects_non_positive_port():
    try:
        run_napari_subscriber(host="127.0.0.1", port=0)
    except ValueError as exc:
        assert "fixed TCP port (>0)" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected ValueError for non-positive port")


def test_run_napari_subscriber_startup_only_collects_phase_profile(monkeypatch):
    from detm_app.ui.napari import subscriber as napari_subscriber

    captured: dict[str, object] = {"napari_run_called": False, "viewer_closed": False}

    class _FakeSubscriber:
        def __init__(self, *, host, port, timeout_s):
            captured["subscriber_host"] = str(host)
            captured["subscriber_port"] = int(port)
            captured["subscriber_timeout_s"] = float(timeout_s)
            self.recv_frames = 0

        def poll_latest(self):
            return None

        def close(self):
            captured["subscriber_closed"] = True

    class _FakeLabel:
        def __init__(self, _text):
            self._text = _text

        def setWordWrap(self, _value):
            return None

        def setText(self, text):
            self._text = str(text)

    class _FakeSignal:
        def connect(self, callback):
            captured["timer_callback"] = callback

    class _FakeTimer:
        def __init__(self):
            self.timeout = _FakeSignal()

        def setInterval(self, _value):
            return None

        def start(self):
            captured["timer_started"] = True

        def stop(self):
            captured["timer_stopped"] = True

    class _FakeWindow:
        def add_dock_widget(self, _widget, *, name, area):
            captured["dock_name"] = str(name)
            captured["dock_area"] = str(area)

    class _FakeViewer:
        def __init__(self, *, title):
            self.layers = {}
            self.window = _FakeWindow()
            captured["viewer_title"] = str(title)

        def close(self):
            captured["viewer_closed"] = True

    fake_napari_module = types.ModuleType("napari")
    fake_napari_module.Viewer = _FakeViewer
    fake_napari_module.run = lambda: captured.__setitem__("napari_run_called", True)
    fake_qtpy_module = types.ModuleType("qtpy")
    fake_qtpy_module.QtCore = types.SimpleNamespace(QTimer=_FakeTimer)
    fake_qtpy_module.QtWidgets = types.SimpleNamespace(QLabel=_FakeLabel)

    monkeypatch.setitem(sys.modules, "napari", fake_napari_module)
    monkeypatch.setitem(sys.modules, "qtpy", fake_qtpy_module)
    monkeypatch.setattr(napari_subscriber, "TcpVizSubscriber", _FakeSubscriber)
    monkeypatch.setattr(napari_subscriber, "wait_latest_packet", lambda *_args, **_kwargs: None)

    profile: dict[str, object] = {}
    rc = napari_subscriber.run_napari_subscriber(
        host="127.0.0.1",
        port=5588,
        timeout_s=0.01,
        startup_profile=profile,
        startup_only=True,
    )

    assert int(rc) == 0
    assert bool(captured.get("napari_run_called")) is False
    assert bool(captured.get("viewer_closed")) is True
    assert bool(captured.get("subscriber_closed")) is True
    assert profile.get("first_frame_status") == "timeout"
    assert profile.get("first_frame_s") is None
    assert isinstance(profile.get("napari_qt_import_s"), float)
    assert isinstance(profile.get("viewer_create_s"), float)


def test_packet_to_layer_frame_extracts_active_level_from_nested_policy():
    config = DETMConfig(width=6, height=4, backend="numpy")
    state = api.reset(config, seed=41)
    blob = api.serialize(state)
    packet = VizPacket(
        tick=1,
        state_blob=blob,
        signature=None,
        meta={"policy": {"active_level": "L2"}, "other": 7},
    )
    frame = packet_to_layer_frame(packet)
    assert frame.active_level == "L2"
    assert frame.meta == {"policy": {"active_level": "L2"}, "other": 7}


def test_format_status_text_includes_tick_semantics_from_meta():
    frame = NapariFrame(
        tick=12,
        signature=[0.1, 0.2, 0.3],
        active_level="L1",
        meta={
            "active_level": "L1",
            "chunk_n_ticks": 1,
            "requested_n_ticks": 200,
            "step_requested_n_ticks": 200,
            "step_effective_n_ticks": 200,
        },
        layers={},
    )
    text = _format_status_text(
        host="127.0.0.1",
        port=5588,
        frame=frame,
        recv_frames=3,
        rendered_count=2,
    )
    assert "tick=12 recv=3 rendered=2" in text
    assert "active_level=L1" in text
    assert "chunk=1 requested=200 step_requested=200 step_effective=200" in text
    assert "commit_packets: total=0 realtime=0 audit=0" in text
    assert "fabric: disabled" in text


def test_format_status_text_includes_commit_and_fabric_counters():
    frame = NapariFrame(
        tick=21,
        signature=[0.4, 0.5],
        active_level="L0",
        meta={
            "active_level": "L0",
            "chunk_n_ticks": 1,
            "requested_n_ticks": 1,
            "step_requested_n_ticks": 1,
            "step_effective_n_ticks": 1,
            "commit_packets_total": 3,
            "commit_packets_by_mode": {"realtime": 2, "audit": 1},
            "fabric": {
                "commit_count": 3,
                "ack_count": 6,
                "quorum": {"accepted_count": 3, "pending_count": 0, "rejected_count": 0},
                "delivery": {"accepted_count": 3, "pending_count": 0, "rejected_count": 0},
                "replay": {"checks_total": 3, "checks_failed": 0},
            },
        },
        layers={},
    )
    text = _format_status_text(
        host="127.0.0.1",
        port=5588,
        frame=frame,
        recv_frames=10,
        rendered_count=9,
    )
    assert "commit_packets: total=3 realtime=2 audit=1" in text
    assert "fabric: commits=3 acks=6 quorum=3/0/0 delivery=3/0/0 replay=0/3" in text

