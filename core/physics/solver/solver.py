import numpy as np
from utils.constants import CONSTANTS

mu = CONSTANTS["mu"]



def equations_of_motion(
    t: float,
    y: np.ndarray,
    I_inv: np.ndarray,
    I_S: np.ndarray,
    wheel_axes: list,
    tau_ext: np.ndarray,
    alpha_wheels: np.ndarray = None,
    I_R_spin: float = 0.0,
) -> np.ndarray:

    N_R = len(wheel_axes)

    # ================ current state ================
    p = y[0:3]
    v = y[3:6]
    q = y[6:10]  # [qw, qx, qy, qz]
    omega = y[10:13]
    omega_rw = y[13 : 13 + N_R] if len(y) >= 13 + N_R else np.zeros(N_R)

    # ================================================

    if alpha_wheels is None:
        alpha_wheels = np.zeros(N_R)

    # ==================== gravity ===================
    r_norm = np.linalg.norm(p)
    a_grav = -mu * p / (r_norm**3)
    # ================================================

    # ==================== control ===================

    # Bdot
    
    # reaction wheels
    
    # ================================================

    # =================== rotation ===================
    wx, wy, wz = omega
    kinematic_matrix = np.array([
        [0.0, -wx, -wy, -wz],
        [wx,  0.0,  wz, -wy],
        [wy, -wz,  0.0,  wx],
        [wz,  wy, -wx,  0.0]
    ])
    dq_dt = 0.5 *( kinematic_matrix @ q)


    h_R = np.zeros(3, dtype=float)
    tau_RW_reaction = np.zeros(3, dtype=float)

    for i, axis in enumerate(wheel_axes):
        n_i = axis / np.linalg.norm(axis)
        h_R += I_R_spin * omega_rw[i] * n_i
        tau_RW_reaction += I_R_spin * alpha_wheels[i] * n_i

    H = I_S @ omega + h_R
    total_torque = tau_ext + tau_RW_reaction - np.cross(omega, H)
    domega_dt = I_inv @ total_torque

    domega_rw_dt = alpha_wheels
    # ================================================

    return np.hstack([v, a_grav, dq_dt, domega_dt, domega_rw_dt])


def rk4_step(func, t: float, y: np.ndarray, dt: float, *args) -> np.ndarray:
    """Klasyczny algorytm Rungego-Kutty 4. rzędu."""
    k1 = func(t, y, *args)
    k2 = func(t + 0.5 * dt, y + 0.5 * dt * k1, *args)
    k3 = func(t + 0.5 * dt, y + 0.5 * dt * k2, *args)
    k4 = func(t + dt, y + dt * k3, *args)

    return y + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)