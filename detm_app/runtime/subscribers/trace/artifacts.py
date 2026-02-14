from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from detm.runtime import api
from detm.runtime.config import DETMConfig
from detm.runtime.state import DETMState


@dataclass
class ArtifactWriter:
    """Writes `state.msgpack`, `digest.json`, and `config.json` on close."""

    out_dir: Path
    _unsub_close: Callable[[], None] | None = None

    @classmethod
    def attach(cls, bus, out_dir: Path) -> "ArtifactWriter":
        writer = cls(out_dir=out_dir)
        writer._unsub_close = bus.add_event_listener_unsub("close", writer.on_close)
        return writer

    def on_close(
        self,
        *,
        config: DETMConfig,
        state: DETMState,
        **_rest: Any,
    ) -> None:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        (self.out_dir / "config.json").write_text(json.dumps(config.to_dict(), indent=2), encoding="utf-8")
        (self.out_dir / "state.msgpack").write_bytes(api.serialize(state))
        digest = api.digest(state)
        (self.out_dir / "digest.json").write_text(json.dumps(digest.as_dict(), indent=2), encoding="utf-8")
        self.detach()

    def detach(self) -> None:
        if self._unsub_close is not None:
            self._unsub_close()
            self._unsub_close = None


__all__ = ["ArtifactWriter"]
