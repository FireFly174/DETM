from __future__ import annotations

import time
from typing import Any, Callable, Dict, Mapping

import numpy as np

from detm_app.transport.subscriber import TcpVizSubscriber, VizPacket
from detm.runtime.signature import project_field_plane_any


def _select_plane_any(array: Any, *, plane_index: tuple[int, ...] | None = None) -> Any:
    if plane_index is None:
        return project_field_plane_any(array)
    try:
        import torch  # type: ignore
    except ModuleNotFoundError:
        torch = None
    if torch is not None and isinstance(array, torch.Tensor):
        dims = int(array.ndim)
        expected_len = max(0, dims - 2)
        if len(tuple(plane_index)) != expected_len:
            raise ValueError(
                f"plane index length {len(tuple(plane_index))} does not match field leading rank {expected_len}"
            )
        return array[tuple(int(value) for value in tuple(plane_index))]
    out = np.asarray(array)
    dims = int(out.ndim)
    expected_len = max(0, dims - 2)
    if len(tuple(plane_index)) != expected_len:
        raise ValueError(
            f"plane index length {len(tuple(plane_index))} does not match field leading rank {expected_len}"
        )
    return out[tuple(int(value) for value in tuple(plane_index))]


def to_numpy_2d(
    array: Any,
    *,
    height: int,
    width: int,
    plane_index: tuple[int, ...] | None = None,
) -> np.ndarray:
    selected = _select_plane_any(array, plane_index=plane_index)
    try:
        import torch  # type: ignore
    except ModuleNotFoundError:
        torch = None
    if torch is not None and isinstance(selected, torch.Tensor):
        out = selected.detach().to("cpu").numpy()
    else:
        out = np.asarray(selected)
    return out.astype(np.float32, copy=False).reshape(int(height), int(width))


def state_to_layers(state: Any, plane_index: tuple[int, ...] | None = None) -> Dict[str, np.ndarray]:
    lattice = state.lattice
    return {
        "energy": to_numpy_2d(
            state.field_state.energy,
            height=lattice.height,
            width=lattice.width,
            plane_index=plane_index,
        ),
        "entropy": to_numpy_2d(
            state.field_state.entropy,
            height=lattice.height,
            width=lattice.width,
            plane_index=plane_index,
        ),
        "internal_time": to_numpy_2d(
            state.field_state.internal_time,
            height=lattice.height,
            width=lattice.width,
            plane_index=plane_index,
        ),
    }


def extract_active_level(meta: Any) -> str | None:
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


def packet_to_layer_frame(
    packet: VizPacket,
    *,
    deserialize: Callable[[bytes], Any],
    frame_factory: Callable[..., Any],
    state_to_layers_fn: Callable[[Any], Dict[str, np.ndarray]] = state_to_layers,
    extract_active_level_fn: Callable[[Any], str | None] = extract_active_level,
) -> Any:
    state = deserialize(packet.state_blob)
    meta = dict(packet.meta) if isinstance(packet.meta, dict) else {}
    return frame_factory(
        tick=int(packet.tick),
        signature=None if packet.signature is None else [float(x) for x in list(packet.signature)],
        active_level=extract_active_level_fn(meta),
        meta=meta,
        layers=state_to_layers_fn(state),
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


class LayerPresenter:
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

    def render(self, frame: Any) -> None:
        for name, image in dict(frame.layers).items():
            if name in self._viewer.layers:
                layer = self._viewer.layers[name]
                layer.data = image
            else:
                layer = self._viewer.add_image(image, name=name)
            self._autoscale_layer(layer)


def format_status_text(
    *,
    host: str,
    port: int,
    frame: Any,
    recv_frames: int,
    rendered_count: int,
) -> str:
    sig = [] if frame.signature is None else list(frame.signature)
    meta = dict(frame.meta) if isinstance(frame.meta, dict) else {}
    chunk_n_ticks = int(meta.get("chunk_n_ticks", 0))
    requested_n_ticks = int(meta.get("requested_n_ticks", 0))
    step_requested_n_ticks = int(meta.get("step_requested_n_ticks", 0))
    step_effective_n_ticks = int(meta.get("step_effective_n_ticks", 0))
    commit_packets_total = int(meta.get("commit_packets_total", 0))
    commit_packets_by_mode_raw = meta.get("commit_packets_by_mode")
    commit_packets_by_mode = (
        {str(k): int(v) for k, v in dict(commit_packets_by_mode_raw).items()}
        if isinstance(commit_packets_by_mode_raw, Mapping)
        else {}
    )
    fabric_raw = meta.get("fabric")
    fabric = dict(fabric_raw) if isinstance(fabric_raw, Mapping) else {}
    fabric_quorum = dict(fabric.get("quorum", {})) if isinstance(fabric.get("quorum"), Mapping) else {}
    fabric_delivery = dict(fabric.get("delivery", {})) if isinstance(fabric.get("delivery"), Mapping) else {}
    fabric_replay = dict(fabric.get("replay", {})) if isinstance(fabric.get("replay"), Mapping) else {}
    commit_packets_realtime = int(commit_packets_by_mode.get("realtime", 0))
    commit_packets_audit = int(commit_packets_by_mode.get("audit", 0))
    fabric_line = (
        "fabric: disabled"
        if not fabric
        else (
            "fabric: "
            + f"commits={int(fabric.get('commit_count', 0))} "
            + f"acks={int(fabric.get('ack_count', 0))} "
            + "quorum="
            + f"{int(fabric_quorum.get('accepted_count', 0))}/"
            + f"{int(fabric_quorum.get('pending_count', 0))}/"
            + f"{int(fabric_quorum.get('rejected_count', 0))} "
            + "delivery="
            + f"{int(fabric_delivery.get('accepted_count', 0))}/"
            + f"{int(fabric_delivery.get('pending_count', 0))}/"
            + f"{int(fabric_delivery.get('rejected_count', 0))} "
            + "replay="
            + f"{int(fabric_replay.get('checks_failed', 0))}/"
            + f"{int(fabric_replay.get('checks_total', 0))}"
        )
    )
    return (
        f"status: connected {host}:{int(port)}\n"
        + f"tick={int(frame.tick)} recv={int(recv_frames)} rendered={int(rendered_count)}\n"
        + f"active_level={str(frame.active_level or 'n/a')}\n"
        + "ticks: "
        + f"chunk={int(chunk_n_ticks)} requested={int(requested_n_ticks)} "
        + f"step_requested={int(step_requested_n_ticks)} step_effective={int(step_effective_n_ticks)}\n"
        + "commit_packets: "
        + f"total={int(commit_packets_total)} realtime={int(commit_packets_realtime)} audit={int(commit_packets_audit)}\n"
        + f"{fabric_line}\n"
        + f"signature[:4]={sig[:4]}"
    )


__all__ = [
    "LayerPresenter",
    "extract_active_level",
    "format_status_text",
    "packet_to_layer_frame",
    "state_to_layers",
    "to_numpy_2d",
    "wait_latest_packet",
]
