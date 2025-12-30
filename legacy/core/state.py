# core/state.py
import numpy as np

class State:
    def __init__(self, N=100, E_level=0.2, seed=None):
        if seed is not None:
            np.random.seed(seed)

        self.N = N
        self.E_level = E_level

        self.E = np.random.rand(N, N) * E_level
        self.E[N//2, N//2] = 0.9

        self.S = np.zeros((N, N), dtype=float)
        self.Jx = np.zeros((N, N), dtype=float)
        self.Jy = np.zeros((N, N), dtype=float)

        self.tau = np.zeros((N, N), dtype=float)
        self.mu_bar = 0.0

        self.t_global = 0.0
