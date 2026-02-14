"""Visualization/runtime helpers for Tk runner launcher."""

from __future__ import annotations

import time
from typing import Any

from detm_app.transport.subscriber import TcpVizSubscriber


class TkVizFlow:
    def __init__(self, *, settings: Any, runner: Any, viz_panel: Any) -> None:
        self._settings = settings
        self._runner = runner
        self._viz_panel = viz_panel
        self._tcp_subscriber: TcpVizSubscriber | None = None
        self._tcp_sub_key: tuple[str, str, int] | None = None
        self._tcp_rendered_frames = 0

        self._last_embedded_step = -1
        self._embedded_draws = 0
        self._embedded_fps_ema = 0.0
        self._embedded_window_start = 0.0
        self._embedded_window_count = 0

    def close(self) -> None:
        self._disable_tcp_subscriber()

    def _disable_tcp_subscriber(self) -> None:
        if self._tcp_subscriber is not None:
            try:
                self._tcp_subscriber.close()
            except Exception:
                pass
            self._tcp_subscriber = None
        self._tcp_sub_key = None
        self._tcp_rendered_frames = 0

    def _configure_tcp_subscriber(self) -> None:
        if not bool(self._settings.viz_enabled):
            self._disable_tcp_subscriber()
            return
        transport_name = str(self._settings.viz_transport).strip().lower() or "embedded"
        if transport_name != "tcp":
            self._disable_tcp_subscriber()
            return

        host = str(self._settings.viz_host).strip() or "127.0.0.1"
        port = int(self._settings.viz_port)
        if port <= 0 and getattr(self._runner, "_viz_transport", None) is not None:
            try:
                viz_transport = getattr(self._runner, "_viz_transport")
                if hasattr(viz_transport, "address"):
                    address = getattr(viz_transport, "address")
                    if isinstance(address, tuple) and len(address) == 2:
                        host = str(address[0])
                        port = int(address[1])
            except Exception:
                pass

        key = ("tcp", host, int(port))
        if self._tcp_sub_key == key and self._tcp_subscriber is not None:
            return

        self._disable_tcp_subscriber()
        if int(port) <= 0:
            return
        try:
            self._tcp_subscriber = TcpVizSubscriber(host, int(port))
            self._tcp_sub_key = key
            self._tcp_rendered_frames = 0
        except Exception:
            self._tcp_subscriber = None
            self._tcp_sub_key = None
            self._tcp_rendered_frames = 0

    def update_embedded(self, *, force: bool = False) -> None:
        if not bool(self._settings.viz_enabled):
            self._viz_panel.status_var.set("Viz: disabled")
            return
        transport = str(self._settings.viz_transport).strip().lower() or "embedded"
        if transport != "embedded":
            self._viz_panel.status_var.set(f"Viz: {transport}")
            return
        step = int(self._runner.state.step_count)
        every = max(1, int(getattr(self._settings, "viz_every_steps", 1) or 1))
        if not force and self._last_embedded_step >= 0 and (step - self._last_embedded_step) < every:
            return
        self._last_embedded_step = step
        try:
            signature = list(self._runner.last_observables) if self._runner.last_observables is not None else None
            self._viz_panel.update_from_state(state=self._runner.state, tick=step, signature=signature)
            self._embedded_draws += 1
            now = time.perf_counter()
            if self._embedded_window_start <= 0.0:
                self._embedded_window_start = now
                self._embedded_window_count = 0
            self._embedded_window_count += 1
            dt = now - self._embedded_window_start
            if dt >= 0.5:
                fps = float(self._embedded_window_count) / max(1e-9, dt)
                self._embedded_fps_ema = 0.85 * float(self._embedded_fps_ema) + 0.15 * fps
                self._embedded_window_start = now
                self._embedded_window_count = 0
            self._viz_panel.status_var.set(
                self._viz_panel.status_var.get() + f"  embedded={self._embedded_draws}~{self._embedded_fps_ema:.1f}fps"
            )
        except Exception as exc:
            self._viz_panel.status_var.set(f"Viz: error ({exc})")

    def update_tcp(self) -> None:
        if not bool(self._settings.viz_enabled):
            self._viz_panel.status_var.set("Viz: disabled")
            return
        transport = str(self._settings.viz_transport).strip().lower() or "embedded"
        if transport != "tcp":
            return
        self._configure_tcp_subscriber()
        if self._tcp_subscriber is None:
            self._viz_panel.status_var.set("Viz: tcp (no connection)")
            return
        packet = self._tcp_subscriber.poll_latest()
        if packet is None:
            self._viz_panel.status_var.set(
                f"Viz: tcp (recv={self._tcp_subscriber.recv_frames}, rendered={self._tcp_rendered_frames})"
            )
            return
        try:
            self._viz_panel.update_from_state_blob(
                state_blob=packet.state_blob,
                tick=int(packet.tick),
                signature=packet.signature,
            )
            self._tcp_rendered_frames += 1
            sent_frames = None
            viz_transport = getattr(self._runner, "_viz_transport", None)
            if viz_transport is not None and hasattr(viz_transport, "sent_frames"):
                sent_frames = int(getattr(viz_transport, "sent_frames"))
            if sent_frames is not None:
                self._viz_panel.status_var.set(
                    self._viz_panel.status_var.get()
                    + f"  tcp sent={sent_frames}~{getattr(viz_transport, 'sent_fps_ema', 0.0):.1f}fps"
                    + f" recv={self._tcp_subscriber.recv_frames}~{self._tcp_subscriber.recv_fps_ema:.1f}fps"
                    + f" rendered={self._tcp_rendered_frames}"
                )
            else:
                self._viz_panel.status_var.set(
                    self._viz_panel.status_var.get()
                    + f"  tcp recv={self._tcp_subscriber.recv_frames}~{self._tcp_subscriber.recv_fps_ema:.1f}fps"
                    + f" rendered={self._tcp_rendered_frames}"
                )
        except Exception as exc:
            self._viz_panel.status_var.set(f"Viz: tcp error ({exc})")


__all__ = ["TkVizFlow"]
