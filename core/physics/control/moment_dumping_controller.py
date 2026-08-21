import numpy as np


class MomentumDumpingController:
    def __init__(
        self,
        wheel_axes,
        I_R_spin: float,
        max_wheel_speed: float,
        dump_start_ratio: float = 0.70,
        dump_full_ratio: float = 0.90,
        dump_gain: float = 0.01,
        max_dipole: float = 0.2,
        min_magnetic_field: float = 1e-9,
    ):
        self.wheel_axes = [
            np.asarray(axis, dtype=float) / np.linalg.norm(axis)
            for axis in wheel_axes
        ]

        self.I_R_spin = float(I_R_spin)
        self.max_wheel_speed = float(max_wheel_speed)
        self.dump_start_ratio = float(dump_start_ratio)
        self.dump_full_ratio = float(dump_full_ratio)
        self.dump_gain = float(dump_gain)
        self.max_dipole = float(max_dipole)
        self.min_magnetic_field = float(min_magnetic_field)

        self.N_R = len(self.wheel_axes)

        self.J = np.zeros((3, self.N_R), dtype=float)

        for i, axis in enumerate(self.wheel_axes):
            self.J[:, i] = self.I_R_spin * axis

    def compute_control(
        self,
        current_omega_rw: np.ndarray,
        current_b_body: np.ndarray,
    ):
        current_omega_rw = np.asarray(
            current_omega_rw,
            dtype=float,
        )

        current_b_body = np.asarray(
            current_b_body,
            dtype=float,
        )

        b_norm = np.linalg.norm(current_b_body)

        if b_norm < self.min_magnetic_field:
            return (
                np.zeros(3),
                np.zeros(3),
                False,
            )

        h_rw = self.J @ current_omega_rw

        speed_ratio = (
            np.max(np.abs(current_omega_rw))
            / self.max_wheel_speed
        )

        if speed_ratio <= self.dump_start_ratio:
            return (
                np.zeros(3),
                np.zeros(3),
                False,
            )

        denominator = (
            self.dump_full_ratio
            - self.dump_start_ratio
        )

        dump_factor = np.clip(
            (speed_ratio - self.dump_start_ratio)
            / denominator,
            0.0,
            1.0,
        )

        M_desired = (
            -self.dump_gain
            * dump_factor
            * h_rw
        )

        b_hat = current_b_body / b_norm

        M_perpendicular = (
            M_desired
            - np.dot(M_desired, b_hat) * b_hat
        )

        m_cmd = np.cross(
            current_b_body,
            M_perpendicular,
        ) / (b_norm ** 2)

        m_cmd = np.clip(
            m_cmd,
            -self.max_dipole,
            self.max_dipole,
        )

        M_mag = np.cross(
            m_cmd,
            current_b_body,
        )

        return (
            m_cmd,
            M_mag,
            True,
        )