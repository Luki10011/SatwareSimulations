from datetime import datetime, timedelta, timezone

import numpy as np
from core.physics.disturbance.atmoshperic_drag import AtmosphericDragDisturbance
from core.physics.disturbance.gravity_gradient import GravityGradientDisturbance
from core.physics.disturbance.j2_disturbance import J2Disturbance
from utils.constants import CONSTANTS

mu = CONSTANTS["mu"]

gravity_gradient = GravityGradientDisturbance()
j2_disturbance = J2Disturbance()

import numpy as np

def compute_osculating_semi_major_axis(
    r_eci: np.ndarray, 
    v_eci: np.ndarray, 
    mu: float = 3.986004418e14, 
    r_earth: float = 6378137.0
) -> dict:
    """
    Oblicza chwilowe (osculating) elementy orbitalne z równania energii (vis-viva).
    
    Parameters:
    -----------
    r_eci : np.ndarray
        Wektor pozycji w ECI [m] (shape: (3,))
    v_eci : np.ndarray
        Wektor prędkości w ECI [m/s] (shape: (3,))
    mu : float
        Standardowy parametr grawitacyjny Ziemi [m^3 / s^2]
    r_earth : float
        Średni promień Ziemi [m]
        
    Returns:
    --------
    dict z wartościami:
        - r_norm_km: chwilowy promień [km]
        - a_km: półoś wielka [km] (miara energii orbity)
        - e: mimośród orbity
        - hp_km: wysokość perygeum ponad powierzchnię Ziemi [km]
        - ha_km: wysokość apogeum ponad powierzchnię Ziemi [km]
    """
    r_norm = np.linalg.norm(r_eci)
    v_norm = np.linalg.norm(v_eci)
    
    # 1. Obliczenie energii właściwej orbity (v^2 / 2 - mu / r)
    specific_energy = (v_norm**2) / 2.0 - mu / r_norm
    
    # 2. Równanie Vis-Viva na półoś wielką: a = -mu / (2 * epsilon)
    a_m = -mu / (2.0 * specific_energy)
    
    # 3. Wektor momentu pędu h = r x v
    h_vec = np.cross(r_eci, v_eci)
    h_norm = np.linalg.norm(h_vec)
    
    # 4. Mimośród e = sqrt(1 - p/a) gdzie p = h^2 / mu
    p_m = (h_norm**2) / mu
    e_sq = 1.0 - (p_m / a_m)
    e = np.sqrt(max(0.0, e_sq))
    
    # 5. Wysokości perygeum i apogeum
    r_perigee_m = a_m * (1.0 - e)
    r_apogee_m = a_m * (1.0 + e)
    
    return {
        "r_norm_km": r_norm / 1000.0,
        "a_km": a_m / 1000.0,
        "e": e,
        "hp_km": (r_perigee_m - r_earth) / 1000.0,
        "ha_km": (r_apogee_m - r_earth) / 1000.0,
    }

def equations_of_motion(
    t: float,
    y: np.ndarray,
    I_inv: np.ndarray,
    I_total: np.ndarray,
    I_S: np.ndarray,
    wheel_axes: list,
    tau_mag: np.ndarray,
    alpha_wheels: np.ndarray = None,
    I_R_spin: float = 0.0,
    air_drag_model: AtmosphericDragDisturbance = None,
    epoch_start: datetime = None,
) -> np.ndarray:
    
    N_R = len(wheel_axes)

    # 1. Rozpakowanie wektora stanu y
    p = y[0:3]          # Pozycja ECI [m]
    dp_dt = y[3:6]       # Prędkość ECI [m/s]
    q = y[6:10]         # Kwaternion orientacji (ECI -> Body)
    omega = y[10:13]    # Prędkość kątowa w Body [rad/s]

    omega_rw = (
        y[13:13 + N_R]
        if len(y) >= 13 + N_R
        else np.zeros(N_R)
    )

    if alpha_wheels is None:
        alpha_wheels = np.zeros(N_R)

    r_norm = np.linalg.norm(p)

    # 2. Ruch translacyjny (Sferyczna grawitacja + J2 + Opór)
    a_grav = -mu * p / (r_norm ** 3)
    j2_factor = j2_disturbance.compute_disturbance(p, r_norm)
    
    a_drag = np.zeros(3)
    tau_drag = np.zeros(3)

    # 3. Obliczenie oporu atmosferycznego (jeśli model jest przekazany i poprawnie skonfigurowany)
    if air_drag_model is not None and air_drag_model.mass > 0:
        is_dim_valid = (
            air_drag_model.dx > 0 
            and air_drag_model.dy > 0 
            and air_drag_model.dz > 0
        )
        if is_dim_valid:
            # Wyznaczenie aktualnego czasu dla MSIS
            current_dt = epoch_start + timedelta(seconds=float(t))

            # Pobranie siły ECI i momentu obrotowego Body
            f_drag_eci, tau_drag = air_drag_model.compute_disturbance(
                r_eci=p,
                v_eci=dp_dt,
                q_body=q,
                dt=current_dt,
            )
            # Konwersja siły na przyspieszenie ECI
            a_drag = f_drag_eci / air_drag_model.mass

    # Całkowite przyspieszenie liniowe


    # dv_dt = a_grav + j2_factor + a_drag
    dv_dt = a_grav + a_drag


    # 4. Kinematyka obrotowa (pochodna kwaternionu)
    wx, wy, wz = omega
    kinematic_matrix = np.array([
        [0.0, -wx, -wy, -wz],
        [wx,  0.0,  wz, -wy],
        [wy, -wz,  0.0,  wx],
        [wz,  wy, -wx,  0.0],
    ])
    dq_dt = 0.5 * (kinematic_matrix @ q)

    # 5. Dynamika kół reakcyjnych
    h_R = np.zeros(3, dtype=float)
    tau_RW_reaction = np.zeros(3, dtype=float)

    stats = compute_osculating_semi_major_axis(r_eci_m, v_eci_ms)

    print(
        f"[t={t:.0f}s] "
        f"r: {stats['r_norm_km']:.4f} km | "
        f"a: {stats['a_km']:.6f} km | "
        f"e: {stats['e']:.7f} | "
        f"Perygeum: {stats['hp_km']:.3f} km | "
        f"Apogeum: {stats['ha_km']:.3f} km"
    )

    for i, axis in enumerate(wheel_axes):
        n_i = axis / np.linalg.norm(axis)
        h_R += I_R_spin * omega_rw[i] * n_i
        tau_RW_reaction -= I_R_spin * alpha_wheels[i] * n_i

    H = I_S @ omega + h_R

    # 6. Moment grawitacyjny
    tau_gg = gravity_gradient.compute_disturbance(
        r_eci=p,
        q_body=q,
        I_total=I_total
    )

    # 7. Całkowity moment obrotowy działający na satelitę
    total_torque = (
        tau_mag
        # + tau_gg
        + tau_drag
        + tau_RW_reaction
        - np.cross(omega, H)
    )

    domega_dt = I_inv @ total_torque
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