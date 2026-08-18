from typing import Literal

import numpy as np


class BdotController:

    def __init__(self, 
                 k_gain : float,        # [-] 
                 area : float,          # [m^2]
                 max_current : float,   # [A]
                 coil_turns : int       # [-]
                 ):
        self.k_gain = k_gain
        self.area = area
        self.max_current = max_current
        self.coil_turns = coil_turns

    def get_control_current(
        self,
        current_omega_mes: np.ndarray,
        current_b_mes: np.ndarray,
        configuration: Literal["normal", "adaptive"] = "normal",
    ) -> np.ndarray:
        """Oblicza wektor prądu sterującego [A] z ograniczeniem per-oś."""
        b_norm = np.linalg.norm(current_b_mes)
        if b_norm < 1e-12:
            return np.zeros(3)

        # Pochodna pola B z kinematyki: B_dot = -omega x B
        b_dot = -np.cross(current_omega_mes, current_b_mes)

        if configuration == "normal":
            desired_dipole = -self.k_gain * b_dot
        elif configuration == "adaptive":
            desired_dipole = -self.k_gain * (b_dot / b_norm)
        else:
            raise ValueError(f"Nieznana konfiguracja B-dot: {configuration}")

        desired_current = desired_dipole / (self.area * self.coil_turns)

        current_out = np.clip(
            desired_current, -self.max_current, self.max_current
        )

        return current_out

    def get_torque(
        self, current_applied: np.ndarray, current_b_mes: np.ndarray
    ) -> np.ndarray:
        """Oblicza fizyczny moment obrotowy: tau = m x B."""
        dipole_applied = current_applied * self.coil_turns * self.area
        return np.cross(dipole_applied, current_b_mes)