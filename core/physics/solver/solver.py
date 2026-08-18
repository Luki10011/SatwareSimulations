import numpy as np
from utils.constants import CONSTANTS

mu = CONSTANTS["mu"]



def equations_of_motion(
    t: float, 
    y: np.ndarray, 
    I_inv: np.ndarray,
    I_S: np.ndarray,
    I_RBs: np.ndarray,
    wheel_axes,
    tau_ctrl : np.ndarray,
) -> np.ndarray:
    """Równania swobodnego ruchu satelity (bez zakłóceń)."""

    # ================ current state ================
    p = y[0:3]
    v = y[3:6]
    q = y[6:10]  # [qw, qx, qy, qz]
    omega = y[10:13]
    omega_rw = y[13:]

    # ================================================

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


    domega_rw_dt = np.zeros(len(wheel_axes))

    h_wheels = sum(
        I_RBs[i] @ (omega_rw[i] * wheel_axes[i])
        for i in range(len(omega_rw))
    )

    H = I_S @ omega + h_wheels
    I = np.linalg.inv(I_inv)
    domega_dt = I_inv @ (-np.cross(omega, H) + tau_ctrl)
    # ================================================

    return np.hstack([v, a_grav, dq_dt, domega_dt, domega_rw_dt])


def rk4_step(func, t: float, y: np.ndarray, dt: float, *args) -> np.ndarray:
    """Klasyczny algorytm Rungego-Kutty 4. rzędu."""
    k1 = func(t, y, *args)
    k2 = func(t + 0.5 * dt, y + 0.5 * dt * k1, *args)
    k3 = func(t + 0.5 * dt, y + 0.5 * dt * k2, *args)
    k4 = func(t + dt, y + dt * k3, *args)

    return y + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)