"""Compute backends for DETM.

Backends provide the same L0 dynamics via different numerical libraries
(NumPy, Torch, etc.). The API is intentionally small so new backends can be
added without refactoring the runtime integration surface.
"""

from detm.runtime.backends.base import Backend, BackendConfig
from detm.runtime.backends.numpy_backend import NumpyBackend
from detm.runtime.backends.torch_backend import TorchBackend

__all__ = ["Backend", "BackendConfig", "NumpyBackend", "TorchBackend"]
