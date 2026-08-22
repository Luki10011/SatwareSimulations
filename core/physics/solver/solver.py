import numpy as np
from core.physics.disturbance.gravity_gradient import GravityGradientDisturbance
from core.physics.disturbance.j2_disturbance import J2Disturbance
from utils.constants import CONSTANTS

mu = CONSTANTS["mu"]

gravity_gradient = GravityGradientDisturbance()
j2_disturbance = J2Disturbance()


def equations_of_motion(
    t: float,
    y: np.ndarray,
    I_inv: np.ndarray,
    I_total : np.ndarray,
    I_S: np.ndarray,
    wheel_axes: list,
    tau_mag: np.ndarray,
    alpha_wheels: np.ndarray = None,
    I_R_spin: float = 0.0,
) -> np.ndarray:

    N_R = len(wheel_axes)

    p = y[0:3]
    dp_dt = y[3:6]
    q = y[6:10]
    omega = y[10:13]

    omega_rw = (
        y[13:13 + N_R]
        if len(y) >= 13 + N_R
        else np.zeros(N_R)
    )

    if alpha_wheels is None:
        alpha_wheels = np.zeros(N_R)

    r_norm = np.linalg.norm(p)

    a_grav = (
        -mu * p / (r_norm ** 3)
    )

    j2_factor = j2_disturbance.compute_disturbance(p, r_norm)

    dv_dt = a_grav + j2_factor 

    wx, wy, wz = omega

    kinematic_matrix = np.array([
        [0.0, -wx, -wy, -wz],
        [wx,  0.0,  wz, -wy],
        [wy, -wz,  0.0,  wx],
        [wz,  wy, -wx,  0.0],
    ])

    dq_dt = (
        0.5
        * (kinematic_matrix @ q)
    )

    h_R = np.zeros(3, dtype=float)
    tau_RW_reaction = np.zeros(
        3,
        dtype=float,
    )

    for i, axis in enumerate(wheel_axes):
        n_i = (
            axis
            / np.linalg.norm(axis)
        )

        h_R += (
            I_R_spin
            * omega_rw[i]
            * n_i
        )

        tau_RW_reaction -= (
            I_R_spin
            * alpha_wheels[i]
            * n_i
        )

    H = I_S @ omega + h_R

    tau_gg = gravity_gradient.compute_disturbance(
        r_eci=p,
        q_body=q,
        I_total=I_total
    )

    total_torque = (
        tau_mag
        + tau_gg
        + tau_RW_reaction
        - np.cross(omega, H)
    )

    domega_dt = (
        I_inv @ total_torque
    )

    domega_rw_dt = alpha_wheels

    return np.hstack([
        dp_dt,
        dv_dt,
        dq_dt,
        domega_dt,
        domega_rw_dt,
    ])


def rk4_step(func, t: float, y: np.ndarray, dt: float, *args) -> np.ndarray:
    """Klasyczny algorytm Rungego-Kutty 4. rzędu."""
    k1 = func(t, y, *args)
    k2 = func(t + 0.5 * dt, y + 0.5 * dt * k1, *args)
    k3 = func(t + 0.5 * dt, y + 0.5 * dt * k2, *args)
    k4 = func(t + dt, y + dt * k3, *args)

    return y + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)