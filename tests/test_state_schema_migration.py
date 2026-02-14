from __future__ import annotations

import msgpack
import pytest

from detm.runtime.api import digest, reset, step
from detm.runtime.config import DETMConfig
from detm.runtime.influence import DETMInfluence
from detm.runtime.schemas import DETM_STATE_V1
from detm.runtime.serialization import deserialize_state, migrate_state, serialize_state

_LEGACY_STATE_VERSION = "0.0.0"


def _make_state():
    config = DETMConfig(width=6, height=6, initial_noise=0.02, backend="numpy", device="cpu")
    influence = DETMInfluence(symbol_id="test", amplitude=0.05, region=(3, 3, 1))
    state = reset(config, seed=101)
    state, _ = step(state, influence, n_ticks=2, rng=state.restore_rng())
    return state


def test_state_schema_migration_v1_to_legacy_and_back_preserves_digest():
    state = _make_state()
    blob_v1 = serialize_state(state)
    blob_legacy = migrate_state(blob_v1, DETM_STATE_V1, _LEGACY_STATE_VERSION)
    payload_legacy = msgpack.loads(blob_legacy, raw=False)

    assert "state_version" not in payload_legacy

    restored_legacy = deserialize_state(blob_legacy)
    assert restored_legacy.state_version == DETM_STATE_V1
    assert digest(state).vector == digest(restored_legacy).vector

    blob_v1_again = migrate_state(blob_legacy, _LEGACY_STATE_VERSION, DETM_STATE_V1)
    payload_v1_again = msgpack.loads(blob_v1_again, raw=False)
    assert str(payload_v1_again.get("state_version")) == DETM_STATE_V1

    restored_v1_again = deserialize_state(blob_v1_again)
    assert digest(state).vector == digest(restored_v1_again).vector


def test_deserialize_state_migrates_unversioned_legacy_blob():
    state = _make_state()
    blob_v1 = serialize_state(state)
    payload = msgpack.loads(blob_v1, raw=False)
    payload.pop("state_version", None)
    legacy_blob = msgpack.dumps(payload, use_bin_type=True)

    restored = deserialize_state(legacy_blob)
    assert restored.state_version == DETM_STATE_V1
    assert digest(state).vector == digest(restored).vector


def test_migrate_state_rejects_mismatched_or_unsupported_versions():
    state = _make_state()
    blob_v1 = serialize_state(state)

    with pytest.raises(ValueError, match="version mismatch"):
        migrate_state(blob_v1, _LEGACY_STATE_VERSION, DETM_STATE_V1)

    with pytest.raises(ValueError, match="no state migration path"):
        migrate_state(blob_v1, DETM_STATE_V1, "9.9.9")
