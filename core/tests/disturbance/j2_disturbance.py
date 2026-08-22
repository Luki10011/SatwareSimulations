import numpy as np

from core.physics.disturbance.j2_disturbance import J2Disturbance


def test_j2_nodal_precession_rate():
    """Sprawdza, czy uśredniony numeryczny dryf węzła wstępującego (Omega)

    zgadza się z analitycznym wzorem J2.
    """
    from utils.constants import CONSTANTS

    mu = CONSTANTS["mu"]
    r_e = CONSTANTS["R"]
    j2 = CONSTANTS["J2"]

    # Parametry orbity kołowej: 600 km, i = 45 deg
    alt = 600000.0
    a = r_e + alt
    inc = np.radians(45.0)

    # 1. Analityczna średnia szybkość precesji [rad/s]
    n = np.sqrt(mu / a**3)
    domega_dt_analytic = -1.5 * j2 * ((r_e / a) ** 2) * n * np.cos(inc)

    # 2. Numeryczna średnia pochodna po pełnym obrocie (u_arg from 0 to 2pi)
    num_points = 360
    u_vals = np.linspace(0, 2 * np.pi, num_points, endpoint=False)
    domega_dt_samples = []

    j2_dist = J2Disturbance()
    v_norm = np.sqrt(mu / a)

    for u in u_vals:
        # Pozycja i prędkość w ECI dla danego argumentu szerokości u (dla Omega = 0)
        r_eci = np.array([a * np.cos(u), a * np.sin(u) * np.cos(inc), a * np.sin(u) * np.sin(inc)])

        v_eci = np.array([
            -v_norm * np.sin(u),
            v_norm * np.cos(u) * np.cos(inc),
            v_norm * np.cos(u) * np.sin(inc),
        ])

        a_j2 = j2_dist.compute_disturbance(r_eci)

        # Wektor normalny do orbity
        h_vec = np.cross(r_eci, v_eci)
        h_norm = np.linalg.norm(h_vec)
        u_h = h_vec / h_norm

        # Składowa normalna przyspieszenia
        a_h = np.dot(a_j2, u_h)

        # Równanie Gaussa: dOmega/dt = (r * sin(u) / (h * sin(i))) * a_h
        # Dla orbity kołowej r = a
        domega_dt_instant = (a * np.sin(u) * a_h) / (h_norm * np.sin(inc))
        domega_dt_samples.append(domega_dt_instant)

    domega_dt_numeric_avg = np.mean(domega_dt_samples)

    # Test zgadzania się z błędem poniżej 0.1%
    np.testing.assert_allclose(
        domega_dt_numeric_avg, domega_dt_analytic, rtol=1e-3
    )