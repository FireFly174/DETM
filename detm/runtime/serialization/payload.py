"""Low-level payload helpers for runtime state serialization."""

from __future__ import annotations

from typing import Any, Dict

import msgpack
import numpy as np

# Legacy blobs created before explicit state_version tagging.
DETM_STATE_LEGACY = "0.0.0"

StatePayload = Dict[str, Any]


def to_numpy(array: Any) -> np.ndarray:
    try:
        import torch  # type: ignore
    except ModuleNotFoundError:
        torch = None

    if torch is not None and isinstance(array, torch.Tensor):
        return array.detach().to("cpu").numpy()
    return np.asarray(array)


def pack_payload(payload: StatePayload) -> bytes:
    return msgpack.dumps(payload, use_bin_type=True)


def unpack_payload(blob: bytes) -> StatePayload:
    data = msgpack.loads(blob, raw=False)
    if not isinstance(data, dict):
        raise ValueError("state blob must unpack to a dictionary payload")
    return dict(data)


def detect_payload_state_version(payload: StatePayload) -> str:
    raw = payload.get("state_version", None)
    if raw is None:
        return DETM_STATE_LEGACY
    text = str(raw).strip()
    return text if text else DETM_STATE_LEGACY


__all__ = [
    "DETM_STATE_LEGACY",
    "StatePayload",
    "detect_payload_state_version",
    "pack_payload",
    "to_numpy",
    "unpack_payload",
]
