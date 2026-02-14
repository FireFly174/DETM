"""Visualization daemon (headless TCP hub).

This process is intentionally UI-free. It receives serialized DETMState blobs
from one or more producers and can optionally broadcast the latest frames to
subscribers (viewers).

Protocol (msgpack over TCP):
- Producer: sends messages `{type:"state", tick:int, state_blob:bytes, ...}`
  and may send `{type:"close"}` before disconnecting.
- Subscriber: sends `{type:"subscribe"}` once; the daemon then streams `state`
  messages back on the same connection.

`start_local_daemon()` uses this module as the default server implementation so
that selecting `tcp` in the UI does not spawn an extra window.
"""

from __future__ import annotations

import argparse
import json
import socket
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from detm_app.transport.protocol import recv_msg, send_msg


@dataclass
class StatePacket:
    tick: int
    state_blob: bytes
    signature: Optional[list[float]] = None
    meta: Optional[Dict[str, Any]] = None


class VizHub:
    def __init__(self, host: str, port: int):
        self.host = str(host)
        self.port = int(port)
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.host, self.port))
        self._sock.listen(8)
        self._sock.settimeout(0.5)

        self._stop = threading.Event()
        self._accept_thread = threading.Thread(target=self._accept_loop, daemon=True)

        self._sub_lock = threading.Lock()
        self._subscribers: List[socket.socket] = []
        self._latest_lock = threading.Lock()
        self._latest: StatePacket | None = None

    @property
    def address(self) -> Tuple[str, int]:
        h, p = self._sock.getsockname()
        return str(h), int(p)

    def start(self) -> None:
        self._accept_thread.start()

    def stop(self) -> None:
        self._stop.set()
        with self._sub_lock:
            for s in list(self._subscribers):
                try:
                    s.close()
                except OSError:
                    pass
            self._subscribers.clear()
        try:
            self._sock.close()
        except OSError:
            pass

    def _accept_loop(self) -> None:
        while not self._stop.is_set():
            try:
                client, _addr = self._sock.accept()
            except OSError:
                continue
            t = threading.Thread(target=self._client_loop, args=(client,), daemon=True)
            t.start()

    def _broadcast(self, packet: StatePacket) -> None:
        with self._sub_lock:
            dead: List[socket.socket] = []
            for sub in list(self._subscribers):
                try:
                    send_msg(
                        sub,
                        {
                            "type": "state",
                            "tick": int(packet.tick),
                            "state_blob": packet.state_blob,
                            "signature": packet.signature,
                            "meta": packet.meta,
                        },
                    )
                except Exception:
                    dead.append(sub)
            for sub in dead:
                try:
                    sub.close()
                except OSError:
                    pass
                try:
                    self._subscribers.remove(sub)
                except ValueError:
                    pass

    def _client_loop(self, client: socket.socket) -> None:
        with client:
            try:
                msg = recv_msg(client)
            except Exception:
                return

            mtype = msg.get("type")
            if mtype == "subscribe":
                with self._sub_lock:
                    self._subscribers.append(client)
                with self._latest_lock:
                    latest = self._latest
                if latest is not None:
                    try:
                        self._broadcast(latest)
                    except Exception:
                        return
                while not self._stop.is_set():
                    time.sleep(0.25)
                return

            if mtype == "close":
                return

            if mtype == "state":
                packet = StatePacket(
                    tick=int(msg.get("tick", 0)),
                    state_blob=msg.get("state_blob", b""),
                    signature=msg.get("signature"),
                    meta=msg.get("meta"),
                )
                with self._latest_lock:
                    self._latest = packet
                self._broadcast(packet)

            while not self._stop.is_set():
                try:
                    msg = recv_msg(client)
                except Exception:
                    return
                mtype = msg.get("type")
                if mtype == "close":
                    return
                if mtype != "state":
                    continue
                packet = StatePacket(
                    tick=int(msg.get("tick", 0)),
                    state_blob=msg.get("state_blob", b""),
                    signature=msg.get("signature"),
                    meta=msg.get("meta"),
                )
                with self._latest_lock:
                    self._latest = packet
                self._broadcast(packet)


def run_daemon(host: str, port: int) -> None:  # pragma: no cover (server)
    hub = VizHub(host, port)
    hub.start()
    ready_host, ready_port = hub.address
    print(json.dumps({"host": ready_host, "port": ready_port}), flush=True)

    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        hub.stop()


def main() -> None:  # pragma: no cover
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", default="127.0.0.1", help="Bind host (default: localhost)")
    ap.add_argument("--port", type=int, default=0, help="Bind port (0 = auto)")
    args = ap.parse_args()
    run_daemon(args.host, args.port)


if __name__ == "__main__":
    main()

