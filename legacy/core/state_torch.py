# core/state_torch.py
from __future__ import annotations

from dataclasses import dataclass

from core.model_torch import require_torch, torch


@dataclass
class TorchState:
    N: int
    E_level: float
    device: str = "cpu"
    dtype: str = "float32"
    seed: int | None = None

    def __post_init__(self):
        require_torch()
        dev = torch.device(self.device)
        dt = torch.float32 if self.dtype == "float32" else torch.float64

        if self.seed is not None:
            torch.manual_seed(int(self.seed))

        N = int(self.N)
        E0 = float(self.E_level)

        # core fields
        self.E = torch.rand((N, N), device=dev, dtype=dt) * E0
        self.E[N // 2, N // 2] = torch.as_tensor(1.8, device=dev, dtype=dt)

        self.S = torch.zeros((N, N), device=dev, dtype=dt)
        self.Jx = torch.zeros((N, N), device=dev, dtype=dt)
        self.Jy = torch.zeros((N, N), device=dev, dtype=dt)

        self.tau = torch.zeros((N, N), device=dev, dtype=dt)
        self.mu_bar = 0.0
        self.t_global = 0.0

    def to(self, device: str):
        """Move tensors to another device."""
        require_torch()
        dev = torch.device(device)
        self.E = self.E.to(dev)
        self.S = self.S.to(dev)
        self.Jx = self.Jx.to(dev)
        self.Jy = self.Jy.to(dev)
        self.tau = self.tau.to(dev)
        return self
