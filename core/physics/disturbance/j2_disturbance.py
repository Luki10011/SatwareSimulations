
from utils.constants import CONSTANTS
import numpy as np

class J2Disturbance:

    def __init__(self):
        self.mu = CONSTANTS["mu"]
        self.J2 = CONSTANTS["J2"]
        self.R_E = CONSTANTS["R"]

    def compute_disturbance(self, pos: np.ndarray, r_norm: float = None) -> np.ndarray:
        r = r_norm if r_norm is not None else np.linalg.norm(pos)

        x, y, z = pos[0], pos[1], pos[2]

        coeff = -(3.0 / 2.0) * self.J2 * (self.mu * (self.R_E**2) / (r**4))

        z_over_r_sq = (z / r) ** 2

        p_x = coeff * (x / r) * (1.0 - 5.0 * z_over_r_sq)
        p_y = coeff * (y / r) * (1.0 - 5.0 * z_over_r_sq)
        p_z = coeff * (z / r) * (3.0 - 5.0 * z_over_r_sq)

        return np.array([p_x, p_y, p_z])