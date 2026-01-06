from __future__ import annotations

from dataclasses import dataclass

from detm.integrations.acgs_backend import ACGSDetmBackend
from detm.runtime.config import DETMConfig


@dataclass(frozen=True, slots=True)
class Influence:
    symbols: list[int]


def test_acgs_backend_signature_shape_and_determinism():
    config = DETMConfig(width=10, height=10, initial_noise=0.0, backend="numpy", device="cpu")

    backend_a = ACGSDetmBackend(config=config, n_ticks_per_step=2)
    backend_b = ACGSDetmBackend(config=config, n_ticks_per_step=2)

    backend_a.reset(seed=123)
    backend_b.reset(seed=123)

    seq = [Influence(symbols=[0]), Influence(symbols=[3]), Influence(symbols=[3]), Influence(symbols=[7])]
    sig_a = [backend_a.step(infl).signature for infl in seq]
    sig_b = [backend_b.step(infl).signature for infl in seq]

    assert sig_a == sig_b
    assert all(len(sig) == 5 for sig in sig_a)


def test_acgs_backend_digest_deterministic():
    config = DETMConfig(width=8, height=8, initial_noise=0.0, backend="numpy", device="cpu")
    backend = ACGSDetmBackend(config=config, n_ticks_per_step=1)
    backend.reset(seed=7)

    d0 = backend.digest()
    backend.step(Influence(symbols=[1]))
    d1 = backend.digest()

    assert d0 != d1

