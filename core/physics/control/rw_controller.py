from typing import List, Tuple
import numpy as np
from utils.rotations import quaternion_multiply


class ReactionWheelsController:
    def __init__(
        self,
        wheel_axes: List[np.ndarray],
        I_R_spin: float,
        I_total: np.ndarray,
        kp: float = 0.07,
        kd: float = 1.5,
        max_alpha: float = 15.0,
        max_speed: float = 600.0,
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

        self.rw_saturated = False
        self.N_R = len(self.wheel_axes)

        self.J = np.zeros((3, self.N_R), dtype=float)

        for i, n_i in enumerate(self.wheel_axes):
            self.J[:, i] = self.I_R_spin * n_i

        J_JT = self.J @ self.J.T

        if np.linalg.matrix_rank(J_JT) == 3:
            self.J_pinv = self.J.T @ np.linalg.inv(J_JT)
        else:
            self.J_pinv = np.linalg.pinv(self.J)

    def set_gains(
        self,
        kp: float,
        kd: float,
    ) -> None:
        self.kp = kp
        self.kd = kd

    def reset_saturation(self) -> None:
        self.rw_saturated = False

    def compute_control(
        self,
        current_quat: np.ndarray,
        target_quat: np.ndarray,
        current_omega: np.ndarray,
        current_omega_rw: np.ndarray,
        target_omega: np.ndarray = np.zeros(3),
        max_angle_error_rad: float = 0.35,
    ) -> Tuple[np.ndarray, np.ndarray]:

        q_curr_inv = np.array([
            current_quat[0],
            -current_quat[1],
            -current_quat[2],
            -current_quat[3],
        ])

        q_err = quaternion_multiply(
            q_curr_inv,
            target_quat,
        )

        if q_err[0] < 0:
            q_err = -q_err

        dot = np.clip(
            np.abs(q_err[0]),
            -1.0,
            1.0,
        )

        angle_deg_error = np.degrees(
            2.0 * np.arccos(dot)
        )

      

        e_angle = 2.0 * q_err[1:4]

        e_norm = np.linalg.norm(e_angle)

        if e_norm > max_angle_error_rad:
            e_angle = (
                e_angle
                * max_angle_error_rad
                / e_norm
            )

        e_omega = current_omega - target_omega

        h_rw = self.J @ current_omega_rw
        h_sat = self.I_total @ current_omega

        H = h_sat + h_rw

        alpha_desired_body = (
            self.kp * e_angle
            - self.kd * e_omega
        )

        M_desired = (
            self.I_total @ alpha_desired_body
            + np.cross(
                current_omega,
                H,
            )
        )

        rwalphas = (
            -self.J_pinv @ M_desired
        )

        w123dot = np.clip(
            rwalphas,
            -self.max_alpha,
            self.max_alpha,
        )

        speed_ratio = (
            np.abs(current_omega_rw)
            / self.max_speed
        )

        for i in range(self.N_R):
            # if speed_ratio[i] > 0.90:
            #     if (
            #         np.sign(w123dot[i])
            #         == np.sign(current_omega_rw[i])
            #     ):
            #         reduction = np.clip(
            #             1.0
            #             - (
            #                 speed_ratio[i] - 0.90
            #             )
            #             / 0.10,
            #             0.0,
            #             1.0,
            #         )

            #         w123dot[i] *= reduction

            if (
                abs(current_omega_rw[i])
                >= self.max_speed
                and np.sign(w123dot[i])
                == np.sign(current_omega_rw[i])
            ):
                w123dot[i] = 0.0

        LMN_RWs = -self.J @ w123dot

        self.rw_saturated = bool(
            np.any(
                np.abs(current_omega_rw)
                >= 0.90 * self.max_speed
            )
        )

        return (
            w123dot,
            LMN_RWs,
        )