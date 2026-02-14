"""Viewer adapter registry for shell orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ViewerAdapter:
    viewer_id: str
    entrypoint: str


def build_napari_viewer_args(parsed: Any, *, forwarded_args: list[str]) -> list[str]:
    out = [
        "--host",
        str(parsed.host),
        "--port",
        str(int(parsed.port)),
        "--poll-ms",
        str(int(parsed.poll_ms)),
        "--timeout-s",
        str(float(parsed.timeout_s)),
        "--producer-wait-timeout-s",
        str(float(parsed.producer_wait_timeout_s)),
        "--title",
        str(parsed.title),
    ]
    if bool(parsed.autoscale):
        out.append("--autoscale")
    if bool(parsed.viewer_only):
        out.append("--viewer-only")
    if forwarded_args:
        out.extend(["--", *forwarded_args])
    return out


def build_napari_viewer_options(parsed: Any) -> dict[str, Any]:
    return {
        "host": str(parsed.host),
        "port": int(parsed.port),
        "poll_ms": int(parsed.poll_ms),
        "timeout_s": float(parsed.timeout_s),
        "producer_wait_timeout_s": float(parsed.producer_wait_timeout_s),
        "autoscale": bool(parsed.autoscale),
        "title": str(parsed.title),
        "viewer_only": bool(parsed.viewer_only),
    }


def run_napari_viewer(parsed: Any, *, forwarded_args: list[str]) -> int:
    from detm_app.ui.napari.lab import main as napari_lab_main

    return int(napari_lab_main(build_napari_viewer_args(parsed, forwarded_args=forwarded_args)))


_VIEWER_ADAPTERS: dict[str, ViewerAdapter] = {
    "napari": ViewerAdapter(
        viewer_id="napari",
        entrypoint="detm_app.ui.napari.lab.main",
    ),
}


def resolve_viewer_adapter(viewer: str) -> ViewerAdapter | None:
    key = str(viewer or "").strip().lower()
    if key in {"", "none"}:
        return None
    return _VIEWER_ADAPTERS.get(key)


__all__ = [
    "ViewerAdapter",
    "build_napari_viewer_args",
    "build_napari_viewer_options",
    "resolve_viewer_adapter",
    "run_napari_viewer",
]
