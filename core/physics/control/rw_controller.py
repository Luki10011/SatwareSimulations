from typing import List, Tuple
import numpy as np
from utils.rotations import quaternion_multiply

class ReactionWheelsController:
    """Kontroler orientacji oparty na kołach reakcyjnych z pełną obsługą nasycenia prędkości i rozładowywania (desaturacji)."""

    def __init__(
        self,
        wheel_axes: List[np.ndarray],
        I_R_spin: float,
        I_total: np.ndarray,
        kp: float = 0.07,
        kd: float = 1.5,
        max_alpha: float = 3.0,  # [rad/s^2] maxAlpha
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
        current_quat: np.ndarray,
        target_quat: np.ndarray,
        current_omega: np.ndarray,
        current_omega_rw: np.ndarray,  # w123
        target_omega: np.ndarray = np.zeros(3),
        max_angle_error_rad : float = 0.35
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Wyznacza przyspieszenia kół (w123dot) oraz moment wywierany na kadłub (LMN_RWs)."""

        q_curr_inv = np.array(
            [current_quat[0], -current_quat[1], -current_quat[2], -current_quat[3]]
        )
        q_err = quaternion_multiply(target_quat, q_curr_inv)

        if q_err[0] < 0:
            q_err = -q_err

        e_angle = 2.0 * q_err[1:4]

        # Ograniczenie amplitudy błędu (Slew rate limit)
        e_norm = np.linalg.norm(e_angle)
        if e_norm > max_angle_error_rad:
            e_angle = e_angle * (max_angle_error_rad / e_norm)

        e_omega = current_omega - target_omega

        # Dodatnie kp dla e_angle, ujemne kd dla tłumienia prędkości kątowej
        alpha_desired_body = self.kp * e_angle - self.kd * e_omega
        M_desired = self.I_total @ alpha_desired_body

        # 2. Wyznaczenie wstępnych przyspieszeń kół (rwalphas)
        rwalphas = self.J_pinv @ M_desired

        # 3. Pętla nasycenia i wyhamowywania kół 
        w123dot = np.clip(rwalphas, -self.max_alpha, self.max_alpha)

        for i in range(self.N_R):
            if (
                abs(current_omega_rw[i]) >= self.max_speed and np.sign(w123dot[i]) == np.sign(current_omega_rw[i])
            ):
                w123dot[i] = 0.0

        LMN_RWs = self.J @ w123dot

        return w123dot, LMN_RWs