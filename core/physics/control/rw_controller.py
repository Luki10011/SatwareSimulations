from typing import List, Tuple
import numpy as np


class ReactionWheelsController:
    """Kontroler orientacji oparty na kołach reakcyjnych z pełną obsługą nasycenia prędkości i rozładowywania (desaturacji)."""

    def __init__(
        self,
        wheel_axes: List[np.ndarray],
        I_R_spin: float,
        I_total: np.ndarray,
        kp: float = 0.07,
        kd: float = 1.5,
        max_alpha: float = 5.0,  # [rad/s^2] maxAlpha
        max_speed: float = 600.0,  # [rad/s] maxSpeed (~5700 RPM)
        aligned_axes: bool = False,
    ):
        self.wheel_axes = [
            np.array(axis, dtype=float) / np.linalg.norm(axis)
            for axis in wheel_axes
        ]
        self.I_R_spin = float(I_R_spin)
        self.I_total = np.array(I_total, dtype=float)
        self.kp = kp
        self.kd = kd
        self.max_alpha = max_alpha
        self.max_speed = max_speed
        self.aligned_axes = aligned_axes

        self.rw_saturated: bool = False
        self.N_R = len(self.wheel_axes)

        # Macierz J (3 x N_R): J_i = I_R_spin * n_i
        self.J = np.zeros((3, self.N_R), dtype=float)
        for i, n_i in enumerate(self.wheel_axes):
            self.J[:, i] = self.I_R_spin * n_i

        J_JT = self.J @ self.J.T
        if np.linalg.matrix_rank(J_JT) == 3:
            self.J_pinv = self.J.T @ np.linalg.inv(J_JT)
        else:
            self.J_pinv = np.linalg.pinv(self.J)

    def set_gains(self, kp: float, kd: float) -> None:
        self.kp = kp
        self.kd = kd

    def reset_saturation(self) -> None:
        """Resetuje stan nasycenia kół."""
        self.rw_saturated = False

    def compute_control(
        self,
        current_euler_rad: np.ndarray,
        target_euler_rad: np.ndarray,
        current_omega: np.ndarray,
        current_omega_rw: np.ndarray,  # w123
        target_omega: np.ndarray = np.zeros(3),
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Wyznacza przyspieszenia kół (w123dot) oraz moment wywierany na kadłub (LMN_RWs)."""
        # 1. Pożądany moment z regulatora PD
        e_angle = (
            current_euler_rad - target_euler_rad + np.pi
        ) % (2 * np.pi) - np.pi
        e_omega = current_omega - target_omega

        alpha_desired_body = -self.kp * e_angle - self.kd * e_omega
        M_desired = self.I_total @ alpha_desired_body

        # 2. Wyznaczenie wstępnych przyspieszeń kół (rwalphas)
        if self.aligned_axes and self.N_R == 3:
            rwalphas = M_desired / self.I_R_spin
        else:
            rwalphas = self.J_pinv @ M_desired

        # 3. Pętla nasycenia i wyhamowywania kół 
        w123dot = np.zeros(self.N_R, dtype=float)

        for idx in range(self.N_R):
            if abs(current_omega_rw[idx]) > self.max_speed:
                w123dot[idx] = 0.0
                if not self.rw_saturated:
                    print(
                        "[RW Controller] Reaction Wheels have Saturated. Moving to desaturization scheme."
                    )
                    self.rw_saturated = True
            else:
                # Ograniczenie przyspieszenia kątowego
                if abs(rwalphas[idx]) > self.max_alpha:
                    rwalphas[idx] = np.sign(rwalphas[idx]) * self.max_alpha
                w123dot[idx] = rwalphas[idx]

            # Procedura desaturacji (spin down)
            if self.rw_saturated:
                w123dot[idx] = -0.1 * current_omega_rw[idx]

        # 4. Liczenie momentu obrotowego LMN_RWs
        # LMN_RWs = Ir1B*w123dot(1)*n1 + Ir2B*w123dot(2)*n2 + Ir3B*w123dot(3)*n3
        LMN_RWs = self.J @ w123dot

        return w123dot, LMN_RWs