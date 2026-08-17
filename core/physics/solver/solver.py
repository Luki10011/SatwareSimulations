import numpy as np
from utils.constants import CONSTANTS

mu = CONSTANTS["mu"]

def equations_of_motion(
    t: float, y: np.ndarray, I_inv: np.ndarray
) -> np.ndarray:
    """Równania swobodnego ruchu satelity (bez zakłóceń)."""
    p = y[0:3]
    v = y[3:6]
    q = y[6:10]  # [qw, qx, qy, qz]
    omega = y[10:13]

    # 1. Translacjonalne (Grawitacja punktowa)
    r_norm = np.linalg.norm(p)
    a_grav = -mu * p / (r_norm**3)

    # 2. Kinematyka kwaternionów dq/dt = 0.5 * q (x) omega
    qw, qx, qy, qz = q
    wx, wy, wz = omega
    dq_dt = 0.5 * np.array(
        [
            -qx * wx - qy * wy - qz * wz,
            qw * wx + qy * wz - qz * wy,
            qw * wy - qx * wz + qz * wx,
            qw * wz + qx * wy - qy * wx,
        ]
    )

    # 3. Dynamika obrotowa (Równanie Eulera bez zewnętrznych momentów: M=0)
    # d(omega)/dt = I^-1 * (-omega x (I * omega))
    I = np.linalg.inv(I_inv)
    domega_dt = I_inv @ (-np.cross(omega, I @ omega))

    return np.hstack([v, a_grav, dq_dt, domega_dt])


def rk4_step(func, t: float, y: np.ndarray, dt: float, *args) -> np.ndarray:
    """Klasyczny algorytm Rungego-Kutty 4. rzędu."""
    k1 = func(t, y, *args)
    k2 = func(t + 0.5 * dt, y + 0.5 * dt * k1, *args)
    k3 = func(t + 0.5 * dt, y + 0.5 * dt * k2, *args)
    k4 = func(t + dt, y + dt * k3, *args)

    return y + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)