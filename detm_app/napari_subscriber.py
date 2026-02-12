"""Napari read-only subscriber for DETM viz daemon frames.

This module implements the canonical napari migration path:
- consume `state` frames via TCP subscribe (`detm_app.subscriber`)
- decode `state_blob` with runtime serialization API
- render state fields as image layers in napari

The module keeps napari imports lazy so tests can run without napari installed.
"""

from __future__ import annotations

import argparse
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Iterable

import numpy as np

from detm.runtime import api
from detm.runtime.state import DETMState
from detm_app.subscriber import TcpVizSubscriber, VizPacket
from detm_app.transport import load_viz_endpoint_registry


def _to_numpy_2d(array: Any, *, height: int, width: int) -> np.ndarray:
    try:
        import torch  # type: ignore
    except ModuleNotFoundError:
        torch = None
    if torch is not None and isinstance(array, torch.Tensor):
        out = array.detach().to("cpu").numpy()
    else:
        out = np.asarray(array)
    return out.astype(np.float32, copy=False).reshape(int(height), int(width))


def state_to_layers(state: DETMState) -> Dict[str, np.ndarray]:
    """Project runtime state into canonical napari layer payload."""
    lattice = state.lattice
    return {
        "energy": _to_numpy_2d(
            state.field_state.energy,
            height=lattice.height,
            width=lattice.width,
        ),
        "entropy": _to_numpy_2d(
            state.field_state.entropy,
            height=lattice.height,
            width=lattice.width,
        ),
        "internal_time": _to_numpy_2d(
            state.field_state.internal_time,
            height=lattice.height,
            width=lattice.width,
        ),
    }


@dataclass(frozen=True)
class NapariFrame:
    tick: int
    signature: list[float] | None
    active_level: str | None
    meta: Dict[str, Any]
    layers: Dict[str, np.ndarray]


def _extract_active_level(meta: Any) -> str | None:
    if not isinstance(meta, dict):
        return None
    direct = str(meta.get("active_level", "")).strip()
    if direct:
        return direct
    policy = meta.get("policy")
    if isinstance(policy, dict):
        value = str(policy.get("active_level", "")).strip()
        if value:
            return value
    level_policy = meta.get("level_policy")
    if isinstance(level_policy, dict):
        value = str(level_policy.get("active_level", "")).strip()
        if value:
            return value
    return None


def packet_to_layer_frame(packet: VizPacket) -> NapariFrame:
    state = api.deserialize(packet.state_blob)
    meta = dict(packet.meta) if isinstance(packet.meta, dict) else {}
    return NapariFrame(
        tick=int(packet.tick),
        signature=None if packet.signature is None else [float(x) for x in list(packet.signature)],
        active_level=_extract_active_level(meta),
        meta=meta,
        layers=state_to_layers(state),
    )


def wait_latest_packet(
    subscriber: TcpVizSubscriber,
    *,
    timeout_s: float = 2.0,
    poll_interval_s: float = 0.01,
) -> VizPacket | None:
    deadline = time.perf_counter() + max(0.0, float(timeout_s))
    while True:
        pkt = subscriber.poll_latest()
        if pkt is not None:
            return pkt
        if time.perf_counter() >= deadline:
            return None
        time.sleep(max(0.001, float(poll_interval_s)))


class _LayerPresenter:
    def __init__(self, viewer: Any, *, autoscale: bool = False) -> None:
        self._viewer = viewer
        self._autoscale = bool(autoscale)

    def _autoscale_layer(self, layer: Any) -> None:
        if not self._autoscale:
            return
        arr = np.asarray(getattr(layer, "data", None))
        if arr.size <= 0:
            return
        vmin = float(np.nanmin(arr))
        vmax = float(np.nanmax(arr))
        if np.isfinite(vmin) and np.isfinite(vmax) and vmin < vmax:
            layer.contrast_limits = (vmin, vmax)

    def render(self, frame: NapariFrame) -> None:
        for name, image in frame.layers.items():
            if name in self._viewer.layers:
                layer = self._viewer.layers[name]
                layer.data = image
            else:
                layer = self._viewer.add_image(image, name=name)
            self._autoscale_layer(layer)


def run_napari_subscriber(
    *,
    host: str,
    port: int,
    poll_ms: int = 40,
    timeout_s: float = 2.0,
    autoscale: bool = False,
    title: str = "DETM napari subscriber (read-only)",
) -> int:
    if int(port) <= 0:
        raise ValueError("Napari subscriber requires a fixed TCP port (>0)")
    # Prefer LGPL-friendly Qt binding when caller did not pin an alternative.
    os.environ.setdefault("QT_API", "pyside6")
    try:
        import napari
        from qtpy import QtCore, QtWidgets
    except Exception as exc:  # pragma: no cover - optional dependency branch
        raise RuntimeError("napari + qtpy are required for napari subscriber mode") from exc

    try:
        subscriber = TcpVizSubscriber(host=str(host), port=int(port), timeout_s=float(timeout_s))
    except Exception as exc:
        raise RuntimeError(
            f"Cannot connect to viz daemon at {host}:{int(port)}. "
            + "Start producer with --viz --viz-transport tcp "
            + "or pass explicit --port/DETM_VIZ_PORT."
        ) from exc
    viewer = napari.Viewer(title=str(title))
    presenter = _LayerPresenter(viewer, autoscale=bool(autoscale))

    rendered = {"count": 0}
    status_label = QtWidgets.QLabel("status: waiting for frames...")
    status_label.setWordWrap(True)
    viewer.window.add_dock_widget(status_label, name="DETM", area="right")

    def _render_packet(pkt: VizPacket) -> None:
        frame = packet_to_layer_frame(pkt)
        presenter.render(frame)
        rendered["count"] += 1
        sig = [] if frame.signature is None else list(frame.signature)
        status_label.setText(
            f"status: connected {host}:{int(port)}\n"
            + f"tick={int(frame.tick)} "
            + f"recv={int(subscriber.recv_frames)} rendered={int(rendered['count'])}\n"
            + f"active_level={str(frame.active_level or 'n/a')}\n"
            + f"signature[:4]={sig[:4]}"
        )

    timer = QtCore.QTimer()

    def _poll() -> None:
        pkt = subscriber.poll_latest()
        if pkt is None:
            return
        try:
            _render_packet(pkt)
        except Exception as exc:
            status_label.setText(f"status: render error: {exc}")

    timer.setInterval(max(10, int(poll_ms)))
    timer.timeout.connect(_poll)
    timer.start()

    # Render immediately if producer already emitted at least one frame.
    first = wait_latest_packet(subscriber, timeout_s=max(0.0, float(timeout_s)))
    if first is not None:
        _render_packet(first)

    try:
        napari.run()
    finally:
        timer.stop()
        subscriber.close()
    return 0


def resolve_napari_endpoint(*, host: str | None, port: int | None) -> tuple[str, int, str]:
    """Resolve endpoint from CLI args, env vars, or producer registry."""
    if port is not None:
        value = int(port)
        if value <= 0:
            raise ValueError("--port must be > 0")
        return (str(host).strip() if host else "127.0.0.1"), value, "cli"

    env_port_raw = str(os.environ.get("DETM_VIZ_PORT", "")).strip()
    if env_port_raw:
        env_port = int(env_port_raw)
        if env_port <= 0:
            raise ValueError("DETM_VIZ_PORT must be > 0")
        env_host = str(os.environ.get("DETM_VIZ_HOST", "")).strip()
        return (str(host).strip() if host else env_host or "127.0.0.1"), env_port, "env"

    registry = load_viz_endpoint_registry()
    if registry is not None:
        reg_host, reg_port = registry
        return (str(host).strip() if host else reg_host), int(reg_port), "registry"

    raise SystemExit(
        "Cannot resolve viz endpoint.\n"
        + "Provide --port, or set DETM_VIZ_PORT, or run a producer that writes runs/viz_endpoint.json.\n"
        + "Example:\n"
        + "  python main.py --viz --viz-transport tcp --viz-port 5588 ...\n"
        + "  python detm_napari_viewer.py --port 5588"
    )


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Napari read-only subscriber for DETM viz daemon.")
    ap.add_argument("--host", default=None, help="Viz daemon host (optional if endpoint auto-discovered)")
    ap.add_argument("--port", type=int, default=None, help="Viz daemon port (must be > 0)")
    ap.add_argument("--poll-ms", type=int, default=40, help="Polling interval in ms")
    ap.add_argument("--timeout-s", type=float, default=2.0, help="TCP connect timeout in seconds")
    ap.add_argument(
        "--autoscale",
        action="store_true",
        help="Autoscale contrast limits after each frame update",
    )
    ap.add_argument(
        "--title",
        default="DETM napari subscriber (read-only)",
        help="Napari window title",
    )
    return ap


def main(argv: Iterable[str] | None = None) -> int:
    args = _build_parser().parse_args(list(argv) if argv is not None else None)
    try:
        host, port, _source = resolve_napari_endpoint(host=args.host, port=args.port)
        return run_napari_subscriber(
            host=str(host),
            port=int(port),
            poll_ms=int(args.poll_ms),
            timeout_s=float(args.timeout_s),
            autoscale=bool(args.autoscale),
            title=str(args.title),
        )
    except RuntimeError as exc:
        msg = str(exc)
        if "napari + qtpy are required" in msg:
            raise SystemExit(
                msg
                + "\nInstall optional deps:\n"
                + "  python -m pip install napari qtpy pyside6"
            ) from exc
        raise SystemExit(msg) from exc


__all__ = [
    "NapariFrame",
    "main",
    "packet_to_layer_frame",
    "resolve_napari_endpoint",
    "run_napari_subscriber",
    "state_to_layers",
    "wait_latest_packet",
]
