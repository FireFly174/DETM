from __future__ import annotations

import warnings


def test_detm_viz_protocol_facade_warns_and_delegates(monkeypatch):
    import detm.viz.protocol as legacy_protocol

    calls = {"send": 0, "recv": 0}

    def _fake_send(sock, payload):
        calls["send"] += 1
        assert payload == {"type": "state"}

    def _fake_recv(sock):
        calls["recv"] += 1
        return {"type": "ok"}

    monkeypatch.setattr(legacy_protocol, "_app_send_msg", _fake_send)
    monkeypatch.setattr(legacy_protocol, "_app_recv_msg", _fake_recv)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        legacy_protocol.send_msg(object(), {"type": "state"})
        msg = legacy_protocol.recv_msg(object())

    assert msg == {"type": "ok"}
    assert calls == {"send": 1, "recv": 1}
    assert any("deprecated" in str(item.message).lower() for item in caught)


def test_detm_viz_client_facade_warns_and_delegates(monkeypatch):
    import detm.viz.client as legacy_client

    monkeypatch.setattr(legacy_client._AppVizClient, "__init__", lambda self, host, port, timeout_s=2.0: None)
    monkeypatch.setattr(legacy_client, "_app_start_local_daemon", lambda **_kwargs: "daemon")

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        client = legacy_client.VizClient("127.0.0.1", 5588)
        daemon = legacy_client.start_local_daemon(host="127.0.0.1", port=0)

    assert isinstance(client, legacy_client._AppVizClient)
    assert daemon == "daemon"
    assert any("deprecated" in str(item.message).lower() for item in caught)


def test_detm_viz_daemon_facade_warns_and_delegates(monkeypatch):
    import detm.viz.daemon as legacy_daemon
    import detm_app.daemon as app_daemon

    calls = {"run": 0, "main": 0}

    monkeypatch.setattr(legacy_daemon._AppVizHub, "__init__", lambda self, host, port: None)
    monkeypatch.setattr(legacy_daemon, "_app_run_daemon", lambda host, port: calls.__setitem__("run", calls["run"] + 1))
    monkeypatch.setattr(app_daemon, "main", lambda: calls.__setitem__("main", calls["main"] + 1))

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        hub = legacy_daemon.VizHub("127.0.0.1", 0)
        legacy_daemon.run_daemon("127.0.0.1", 0)
        legacy_daemon.main()

    assert isinstance(hub, legacy_daemon._AppVizHub)
    assert calls == {"run": 1, "main": 1}
    assert any("deprecated" in str(item.message).lower() for item in caught)


def test_detm_viz_subscriber_facade_warns_and_delegates(monkeypatch):
    import detm.viz.subscriber as legacy_subscriber

    monkeypatch.setattr(
        legacy_subscriber._AppTcpVizSubscriber,
        "__init__",
        lambda self, host, port, timeout_s=2.0: None,
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        sub = legacy_subscriber.TcpVizSubscriber("127.0.0.1", 5588)

    assert isinstance(sub, legacy_subscriber._AppTcpVizSubscriber)
    assert any("deprecated" in str(item.message).lower() for item in caught)


def test_detm_viz_transport_facade_warns_and_delegates(monkeypatch):
    import detm.viz.transport as legacy_transport

    monkeypatch.setattr(legacy_transport._AppTcpVizTransport, "__init__", lambda self, *args, **kwargs: None)
    monkeypatch.setattr(legacy_transport, "_app_write_registry", lambda **_kwargs: None)
    monkeypatch.setattr(legacy_transport, "_app_load_registry", lambda: ("127.0.0.1", 5588))
    monkeypatch.setattr(legacy_transport, "_app_clear_registry", lambda **_kwargs: None)
    monkeypatch.setattr(legacy_transport, "_app_open_transport", lambda **_kwargs: "transport")

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        tr = legacy_transport.TcpVizTransport(client=object())
        legacy_transport.write_viz_endpoint_registry(host="127.0.0.1", port=5588)
        loaded = legacy_transport.load_viz_endpoint_registry()
        legacy_transport.clear_viz_endpoint_registry(host="127.0.0.1", port=5588)
        opened = legacy_transport.open_viz_transport(enabled=True, transport="tcp")

    assert isinstance(tr, legacy_transport._AppTcpVizTransport)
    assert loaded == ("127.0.0.1", 5588)
    assert opened == "transport"
    assert any("deprecated" in str(item.message).lower() for item in caught)


def test_detm_viz_tk_panel_facade_warns_and_delegates(monkeypatch):
    import detm.viz.tk_panel as legacy_panel
    from detm_app.tk_panel import DetmVizPanel as app_panel

    monkeypatch.setattr(legacy_panel._AppDetmVizPanel, "__init__", lambda self, parent: None)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        panel = legacy_panel.DetmVizPanel(parent=object())

    assert isinstance(panel, app_panel)
    assert any("deprecated" in str(item.message).lower() for item in caught)


def test_detm_viz_napari_subscriber_facade_warns_and_delegates(monkeypatch):
    import detm.viz.napari_subscriber as legacy_napari
    import detm_app.napari_subscriber as app_napari

    monkeypatch.setattr(app_napari, "main", lambda _argv=None: 0)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", DeprecationWarning)
        rc = legacy_napari.main([])

    assert int(rc) == 0
    assert any("deprecated" in str(item.message).lower() for item in caught)
