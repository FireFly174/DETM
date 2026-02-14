"""Napari read-only subscriber for DETM viz daemon frames.

This module implements the canonical napari migration path:
- consume `state` frames via TCP subscribe (`detm_app.transport.subscriber`)
- decode `state_blob` with runtime serialization API
- render state fields as image layers in napari

The module keeps napari imports lazy so tests can run without napari installed.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Iterable, MutableMapping

import numpy as np

from detm_app.transport.subscriber import TcpVizSubscriber, VizPacket
from detm_app.transport import load_viz_endpoint_registry
from detm_app.ui.napari import subscriber_flow as _flow

if TYPE_CHECKING:
    from detm.runtime import api as runtime_api_module
    from detm.runtime.state import DETMState

_RUNTIME_API: "runtime_api_module | None" = None


def _patch_six_meta_path_importer() -> None:
    """Work around PySide/shiboken feature-hook incompatibility with six importer on some envs.

    This helper is intentionally no-op when `six` isn't installed.
    """
    for importer in list(sys.meta_path):
        if type(importer).__name__ == "_SixMetaPathImporter" and not hasattr(importer, "_path"):
            try:
                setattr(importer, "_path", [])
            except Exception:
                continue


def _to_numpy_2d(array: Any, *, height: int, width: int) -> np.ndarray:
    return _flow.to_numpy_2d(array, height=height, width=width)


def _runtime_api():
    global _RUNTIME_API
    if _RUNTIME_API is None:
        from detm.runtime import api as runtime_api

        _RUNTIME_API = runtime_api
    return _RUNTIME_API


def state_to_layers(state: "DETMState") -> Dict[str, np.ndarray]:
    """Project runtime state into canonical napari layer payload."""
    return _flow.state_to_layers(state)


@dataclass(frozen=True)
class NapariFrame:
    tick: int
    signature: list[float] | None
    active_level: str | None
    meta: Dict[str, Any]
    layers: Dict[str, np.ndarray]


def _extract_active_level(meta: Any) -> str | None:
    return _flow.extract_active_level(meta)


def packet_to_layer_frame(packet: VizPacket) -> NapariFrame:
    return _flow.packet_to_layer_frame(
        packet,
        deserialize=_runtime_api().deserialize,
        frame_factory=NapariFrame,
        state_to_layers_fn=state_to_layers,
        extract_active_level_fn=_extract_active_level,
    )


def wait_latest_packet(
    subscriber: TcpVizSubscriber,
    *,
    timeout_s: float = 2.0,
    poll_interval_s: float = 0.01,
) -> VizPacket | None:
    return _flow.wait_latest_packet(
        subscriber,
        timeout_s=float(timeout_s),
        poll_interval_s=float(poll_interval_s),
    )


_LayerPresenter = _flow.LayerPresenter


def _format_status_text(
    *,
    host: str,
    port: int,
    frame: NapariFrame,
    recv_frames: int,
    rendered_count: int,
) -> str:
    return _flow.format_status_text(
        host=str(host),
        port=int(port),
        frame=frame,
        recv_frames=int(recv_frames),
        rendered_count=int(rendered_count),
    )


def run_napari_subscriber(
    *,
    host: str,
    port: int,
    poll_ms: int = 40,
    timeout_s: float = 2.0,
    autoscale: bool = False,
    title: str = "DETM napari subscriber (read-only)",
    startup_profile: MutableMapping[str, Any] | None = None,
    startup_only: bool = False,
) -> int:
    if int(port) <= 0:
        raise ValueError("Napari subscriber requires a fixed TCP port (>0)")
    # Prefer LGPL-friendly Qt binding when caller did not pin an alternative.
    os.environ.setdefault("QT_API", "pyside6")
    _patch_six_meta_path_importer()
    import_started = time.perf_counter()
    try:
        import napari
        from qtpy import QtCore, QtWidgets
    except Exception as exc:  # pragma: no cover - optional dependency branch
        raise RuntimeError("napari + qtpy are required for napari subscriber mode") from exc
    if startup_profile is not None:
        startup_profile["napari_qt_import_s"] = float(time.perf_counter() - import_started)

    try:
        subscriber = TcpVizSubscriber(host=str(host), port=int(port), timeout_s=float(timeout_s))
    except Exception as exc:
        raise RuntimeError(
            f"Cannot connect to viz daemon at {host}:{int(port)}. "
            + "Start producer with --viz --viz-transport tcp "
            + "or pass explicit --port/DETM_VIZ_PORT."
        ) from exc
    viewer_create_started = time.perf_counter()
    try:
        viewer = napari.Viewer(title=str(title))
    except Exception as exc:  # pragma: no cover - environment-specific dependency failures
        subscriber.close()
        raise RuntimeError(
            "Failed to initialize napari viewer runtime. "
            + "Check napari/qt/pyside6 environment consistency."
        ) from exc
    if startup_profile is not None:
        startup_profile["viewer_create_s"] = float(time.perf_counter() - viewer_create_started)
    presenter = _LayerPresenter(viewer, autoscale=bool(autoscale))

    rendered = {"count": 0}
    status_label = QtWidgets.QLabel("status: waiting for frames...")
    status_label.setWordWrap(True)
    viewer.window.add_dock_widget(status_label, name="DETM", area="right")

    def _render_packet(pkt: VizPacket) -> None:
        frame = packet_to_layer_frame(pkt)
        presenter.render(frame)
        rendered["count"] += 1
        status_label.setText(
            _format_status_text(
                host=str(host),
                port=int(port),
                frame=frame,
                recv_frames=int(subscriber.recv_frames),
                rendered_count=int(rendered["count"]),
            )
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
    first_frame_started = time.perf_counter()
    first = wait_latest_packet(subscriber, timeout_s=max(0.0, float(timeout_s)))
    if first is not None:
        _render_packet(first)
        if startup_profile is not None:
            startup_profile["first_frame_s"] = float(time.perf_counter() - first_frame_started)
            startup_profile["first_frame_status"] = "rendered"
    elif startup_profile is not None:
        startup_profile["first_frame_s"] = None
        startup_profile["first_frame_status"] = "timeout"

    if bool(startup_only):
        timer.stop()
        subscriber.close()
        try:
            viewer.close()
        except Exception:
            pass
        return 0

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
        + "  python main.py napari -- --port 5588"
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
    "_format_status_text",
    "main",
    "packet_to_layer_frame",
    "resolve_napari_endpoint",
    "run_napari_subscriber",
    "state_to_layers",
    "wait_latest_packet",
]
