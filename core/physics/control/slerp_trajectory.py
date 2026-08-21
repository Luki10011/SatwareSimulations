import numpy as np

from utils.rotations import quaternion_multiply


def slerp(
    q0: np.ndarray,
    q1: np.ndarray,
    t: float,
) -> np.ndarray:

    q0 = (
        q0
        / np.linalg.norm(q0)
    )

    q1 = (
        q1
        / np.linalg.norm(q1)
    )

    dot = np.dot(q0, q1)

    if dot < 0.0:
        q1 = -q1
        dot = -dot

    dot = np.clip(
        dot,
        -1.0,
        1.0,
    )

    if dot > 0.9995:
        result = (
            q0
            + t * (q1 - q0)
        )

        return (
            result
            / np.linalg.norm(result)
        )

    theta_0 = np.arccos(dot)
    theta = theta_0 * t

    sin_theta = np.sin(theta)
    sin_theta_0 = np.sin(theta_0)

    s0 = (
        np.cos(theta)
        - dot
        * sin_theta
        / sin_theta_0
    )

    s1 = (
        sin_theta
        / sin_theta_0
    )

    result = (
        s0 * q0
        + s1 * q1
    )

    return (
        result
        / np.linalg.norm(result)
    )


class SlerpTrajectoryGenerator:

    def __init__(
        self,
        max_slew_rate_deg_s: float = 2.0,
    ):
        self.max_slew_rate_rad = np.deg2rad(
            max_slew_rate_deg_s
        )

        self.q_start = np.array(
            [1.0, 0.0, 0.0, 0.0]
        )

        self.q_target = np.array(
            [1.0, 0.0, 0.0, 0.0]
        )

        self.axis = np.zeros(3)

        self.angle = 0.0

        self.t_start = 0.0
        self.T_total = 0.0

        self.is_active = False

    def set_new_target(
        self,
        q_current: np.ndarray,
        q_target: np.ndarray,
        t_curr: float,
    ) -> None:

        self.q_start = (
            np.asarray(q_current, dtype=float)
            / np.linalg.norm(q_current)
        )

        self.q_target = (
            np.asarray(q_target, dtype=float)
            / np.linalg.norm(q_target)
        )

        dot = np.dot(
            self.q_start,
            self.q_target,
        )

        if dot < 0.0:
            self.q_target = -self.q_target
            dot = -dot

        dot = np.clip(
            dot,
            -1.0,
            1.0,
        )

        self.angle = (
            2.0
            * np.arccos(dot)
        )

        if self.angle < 1e-8:
            self.axis = np.zeros(3)
            self.T_total = 0.0
            self.t_start = t_curr
            self.is_active = False
            return

        q_start_inv = np.array([
            self.q_start[0],
            -self.q_start[1],
            -self.q_start[2],
            -self.q_start[3],
        ])

        q_err = quaternion_multiply(
            q_start_inv,
            self.q_target,
        )

        if q_err[0] < 0:
            q_err = -q_err

        sin_half = np.sin(
            self.angle / 2.0
        )

        if abs(sin_half) < 1e-8:
            self.axis = np.zeros(3)
        else:
            self.axis = (
                q_err[1:4]
                / sin_half
            )

            axis_norm = np.linalg.norm(
                self.axis
            )

            if axis_norm > 1e-8:
                self.axis /= axis_norm

        self.T_total = (
            1.875
            * self.angle
            / self.max_slew_rate_rad
        )

        self.t_start = t_curr
        self.is_active = True

    def get_command(
        self,
        t_curr: float,
    ) -> tuple[np.ndarray, np.ndarray]:

        if (
            not self.is_active
            or self.T_total <= 0.0
        ):
            return (
                self.q_target.copy(),
                np.zeros(3),
            )

        tau = (
            t_curr - self.t_start
        ) / self.T_total

        tau = np.clip(
            tau,
            0.0,
            1.0,
        )

        if tau >= 1.0:
            self.is_active = False

            return (
                self.q_target.copy(),
                np.zeros(3),
            )

        s = (
            10.0 * tau**3
            - 15.0 * tau**4
            + 6.0 * tau**5
        )

        ds_dt = (
            30.0 * tau**2
            - 60.0 * tau**3
            + 30.0 * tau**4
        ) / self.T_total

        cmd_quat = slerp(
            self.q_start,
            self.q_target,
            s,
        )

        cmd_omega = (
            self.axis
            * self.angle
            * ds_dt
        )

        return (
            cmd_quat,
            cmd_omega,
        )