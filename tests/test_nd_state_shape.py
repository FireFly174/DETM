from __future__ import annotations

import numpy as np

from detm.core.fields import Lattice
from detm.runtime.config import DETMConfig
from detm.runtime.serialization import deserialize_state, serialize_state
from detm.runtime.state import DETMFieldState, DETMState


def test_config_roundtrip_preserves_canonical_shape_and_legacy_aliases():
    cfg = DETMConfig(shape=(3, 5, 7), backend="numpy", device="cpu")

    payload = cfg.to_dict()
    restored = DETMConfig.from_dict(payload)

    assert tuple(payload.get("shape", ())) == (3, 5, 7)
    assert int(payload.get("height", 0)) == 5
    assert int(payload.get("width", 0)) == 7
    assert restored.shape == (3, 5, 7)
    assert int(restored.height) == 5
    assert int(restored.width) == 7


def test_config_from_legacy_width_height_derives_2d_shape():
    restored = DETMConfig.from_dict({"width": 8, "height": 6, "backend": "numpy", "device": "cpu"})

    assert restored.shape == (6, 8)
    assert int(restored.height) == 6
    assert int(restored.width) == 8


def test_state_serialization_preserves_nd_shape_and_lattice_aliases():
    shape = (2, 5, 7)
    lattice = Lattice(width=7, height=5, boundary="periodic")
    energy = np.arange(np.prod(shape), dtype=float).reshape(shape)
    entropy = (energy / 10.0).copy()
    internal_time = np.zeros(shape, dtype=float)
    config = DETMConfig(shape=shape, backend="numpy", device="cpu")
    state = DETMState(
        field_state=DETMFieldState(
            lattice=lattice,
            energy=energy,
            entropy=entropy,
            internal_time=internal_time,
            shape=shape,
        ),
        step_count=4,
        config=config.to_dict(),
    )

    blob = serialize_state(state)
    restored = deserialize_state(blob)

    assert restored.field_state.shape == shape
    assert tuple(np.asarray(restored.field_state.energy).shape) == shape
    assert int(restored.lattice.height) == 5
    assert int(restored.lattice.width) == 7
    assert tuple(restored.config.get("shape", ())) == shape
