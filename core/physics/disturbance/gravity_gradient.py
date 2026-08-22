import numpy as np

from utils.constants import CONSTANTS
from utils.rotations import _rotate_vector_by_quaternion

class GravityGradientDisturbance:
   

    def __init__(self):
       
        self.mu = CONSTANTS["mu"]
    

    def compute_torque(
        self, r_eci: np.ndarray, q_body: np.ndarray, I_total: np.ndarray
    ) -> np.ndarray:
        
        r_norm = np.linalg.norm(r_eci)
        if r_norm < 1e-3:
            return np.zeros(3)

        r_body = _rotate_vector_by_quaternion(r_eci, q_body)

        u_r = r_body / r_norm

        coeff = (3.0 * self.mu) / (r_norm**3)
        I_u_r = I_total @ u_r
        tau_gg = coeff * np.cross(u_r, I_u_r)

        return tau_gg

    def compute_disturbance(
        self, r_eci: np.ndarray, q_body: np.ndarray, I_total: np.ndarray
    ) -> np.ndarray:
       
        return self.compute_torque(r_eci, q_body, I_total)