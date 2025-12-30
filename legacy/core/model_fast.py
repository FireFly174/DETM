# core/model_fast.py
import numpy as np
from core.state import State


class ModelFast:
    """
    Векторная NumPy-реализация Model.step() без Python-циклов.

    ВАЖНО:
    - делаем максимально близко к текущей логике:
      * S зависит от (E-E_level)^2 + вклад соседей (8-соседей)
      * tau += v(S)
      * активные клетки (tau>=1) совершают перенос энергии
      * перенос делаем по двум направлениям как в текущем коде:
        (di=1,dj=0) и (di=0,dj=1) — то есть "вниз" и "вправо"
    """

    def __init__(self, st: State, params):
        self.st = st
        self.p = params

    def time_speed(self, S):
        return 1.0 / (1.0 + self.p.lambda_t * S)

    def update_S(self, E):
        # Базовая часть
        E0 = self.st.E_level
        beta = self.p.beta
        gamma = self.p.gamma

        d = (E - E0)
        S = beta * d * d

        # 8-соседей (как в твоём update_S с di/dj in [-1,0,1], кроме 0,0)
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                if di == 0 and dj == 0:
                    continue
                En = np.roll(np.roll(E, di, axis=0), dj, axis=1)
                dn = (En - E0)
                S += gamma * dn * dn

        return S

    def step(self):
        st = self.st
        p = self.p
        E = st.E

        # 1) S
        S_new = self.update_S(E)
        st.S[:] = S_new

        # 2) mu и глобальная компенсация
        E0 = st.E_level
        beta = p.beta
        mu = 2.0 * beta * (E - E0)
        mu_bar = float(np.mean(mu))
        st.mu_bar = mu_bar
        mu_eff = mu - mu_bar

        # 3) время
        v = self.time_speed(S_new)
        st.tau += v

        # 4) активные клетки
        active = (st.tau >= 1.0)
        st.tau[active] -= 1.0

        # 5) sigma
        # (по твоему смыслу: чем больше энтропия, тем меньше проводимость)
        sigma = np.zeros_like(E, dtype=float)
        sigma[active] = 1.0 / (1.0 + p.alpha * S_new[active])

        # 6) перенос энергии (вниз и вправо) — векторно
        # вниз = (i+1,j): roll(-1, axis=0) даёт E_down[i,j] = E[i+1,j]
        mu_down = np.roll(mu_eff, -1, axis=0)
        mu_right = np.roll(mu_eff, -1, axis=1)

        # phi = kappa * sigma * (mu_eff - mu_neighbor)
        phi_x = p.kappa * sigma * (mu_eff - mu_down)   # поток "вниз"
        phi_y = p.kappa * sigma * (mu_eff - mu_right)  # поток "вправо"

        # Jx/Jy по знаку как у тебя: ты делаешь st.Jx[i,j] -= phi, st.Jy[i,j] -= phi
        st.Jx[:] = -phi_x
        st.Jy[:] = -phi_y

        # E_new = E - out + in
        E_new = E - phi_x - phi_y
        E_new += np.roll(phi_x, 1, axis=0)  # пришло сверху
        E_new += np.roll(phi_y, 1, axis=1)  # пришло слева

        st.E[:] = np.clip(E_new, 0.0, 2.0 * E0)
        st.t_global += 1.0
