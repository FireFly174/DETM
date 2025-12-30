# core/model.py
import numpy as np
from core.state import State

class Model:
    def __init__(self, st: State, params):
        self.st = st
        self.p = params

    def time_speed(self, S):
        return 1.0 / (1.0 + self.p.lambda_t * S)

    def update_S(self, E):
        N = self.st.N
        E_level = self.st.E_level
        beta = self.p.beta
        gamma = self.p.gamma

        S_new = beta * (E - E_level) ** 2
        for i in range(N):
            for j in range(N):
                for di, dj in [(-1,0),(1,0),(0,-1),(0,1)]:
                    ni, nj = (i + di) % N, (j + dj) % N
                    S_new[i, j] += gamma * (E[ni, nj] - E_level) ** 2
        return S_new

    def compute_mu(self, E):
        beta = self.p.beta
        E_level = self.st.E_level
        return 2 * beta * (E - E_level)

    def step(self):
        st, p = self.st, self.p
        N = st.N
        E_level = st.E_level

        E_new = st.E.copy()
        st.Jx.fill(0.0)
        st.Jy.fill(0.0)

        st.S[:] = self.update_S(st.E)

        mu = self.compute_mu(st.E)
        st.mu_bar = float(mu.mean())
        mu_eff = mu - st.mu_bar

        v = self.time_speed(st.S)
        st.tau += v

        for i in range(N):
            for j in range(N):
                if st.tau[i, j] < 1.0:
                    continue

                st.tau[i, j] -= 1.0
                sigma = 1.0 / (1.0 + p.alpha * st.S[i, j])

                for di, dj in [(1,0),(0,1)]:
                    ni, nj = (i + di) % N, (j + dj) % N
                    phi = p.kappa * sigma * (mu_eff[i, j] - mu_eff[ni, nj])

                    E_new[i, j] -= phi
                    E_new[ni, nj] += phi

                    if di == 1:
                        st.Jx[i, j] -= phi
                    else:
                        st.Jy[i, j] -= phi

        st.E[:] = np.clip(E_new, 0.0, 2.0 * E_level)
        st.t_global += 1.0
