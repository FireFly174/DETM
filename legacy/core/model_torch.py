# core/model_torch.py
from __future__ import annotations

try:
    import torch
    import torch.nn.functional as F
except Exception:  # torch may be absent
    torch = None
    F = None


class TorchBackendError(RuntimeError):
    pass


def require_torch():
    if torch is None:
        raise TorchBackendError(
            "PyTorch is not installed. Install it, e.g.:\n"
            "  pip install torch\n"
            "or CUDA build:\n"
            "  pip install torch --index-url https://download.pytorch.org/whl/cu121"
        )


class ModelTorchFast:
    """
    Torch-реализация шага, максимально близкая к core/model_fast.py.
    Работает на CPU/GPU. Опционально можно обернуть в torch.compile в вызывающем коде.
    """

    def __init__(self, st, params):
        require_torch()
        self.st = st
        self.p = params

        # заранее подготовим 3x3 ядро "соседи кроме центра"
        # Оно будет использоваться для суммы (E-E0)^2 по 8 соседям
        k = torch.ones((1, 1, 3, 3), device=st.E.device, dtype=st.E.dtype)
        k[0, 0, 1, 1] = 0.0
        self._k8 = k

    def time_speed(self, S):
        return 1.0 / (1.0 + float(self.p.lambda_t) * S)

    def update_S(self, E):
        """
        Аналог ModelFast.update_S:
          S = beta*(E-E0)^2 + gamma*sum_8neighbors( (E_neighbor-E0)^2 )
        Важно: в numpy-версии соседи берутся с периодическими границами (np.roll).
        Тут делаем circular padding + conv2d.
        """
        E0 = float(self.st.E_level)
        beta = float(self.p.beta)
        gamma = float(self.p.gamma)

        d = (E - E0)
        base = beta * d * d

        # conv по (d^2) с circular padding
        # F.pad поддерживает mode="circular"
        x = (d * d)[None, None, :, :]          # [1,1,N,N]
        x = F.pad(x, (1, 1, 1, 1), mode="circular")
        neigh_sum = F.conv2d(x, self._k8)[0, 0]  # [N,N]

        return base + gamma * neigh_sum

    @torch.no_grad()
    def step(self):
        st = self.st
        p = self.p

        E = st.E

        # 1) S
        S_new = self.update_S(E)
        st.S.copy_(S_new)

        # 2) mu и глобальная компенсация
        E0 = float(st.E_level)
        beta = float(p.beta)

        mu = 2.0 * beta * (E - E0)
        mu_bar = float(mu.mean().item())
        st.mu_bar = mu_bar
        mu_eff = mu - mu_bar

        # 3) время
        v = self.time_speed(S_new)
        st.tau.add_(v)

        # 4) активные клетки
        active = (st.tau >= 1.0)
        st.tau[active] -= 1.0

        # 5) sigma
        sigma = torch.zeros_like(E)
        alpha = float(p.alpha)
        sigma[active] = 1.0 / (1.0 + alpha * S_new[active])

        # 6) перенос энергии (вниз и вправо) — как ModelFast
        kappa = float(p.kappa)

        mu_down = torch.roll(mu_eff, shifts=-1, dims=0)
        mu_right = torch.roll(mu_eff, shifts=-1, dims=1)

        phi_x = kappa * sigma * (mu_eff - mu_down)   # вниз
        phi_y = kappa * sigma * (mu_eff - mu_right)  # вправо

        st.Jx.copy_(-phi_x)
        st.Jy.copy_(-phi_y)

        E_new = E - phi_x - phi_y
        E_new = E_new + torch.roll(phi_x, shifts=1, dims=0)
        E_new = E_new + torch.roll(phi_y, shifts=1, dims=1)

        # clip как в numpy fast: [0, 2*E0]
        E_new = torch.clamp(E_new, 0.0, 2.0 * E0)
        st.E.copy_(E_new)

        st.t_global = float(st.t_global) + 1.0
