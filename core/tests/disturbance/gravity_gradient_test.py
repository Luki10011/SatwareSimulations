import numpy as np
import pytest
from core.physics.disturbance.gravity_gradient import GravityGradientDisturbance
from utils.rotations import _rotate_vector_by_quaternion



def test_gg_spherical_symmetry():
    
    gg = GravityGradientDisturbance()

    r_eci = np.array([7000000.0, 0.0, 0.0])  # Orbita 7000 km
    q_body = np.array([1.0, 0.0, 0.0, 0.0])  # Brak obrotu
    I_sym = np.diag([0.01, 0.01, 0.01])  # Idealna sfera bezwładności

    tau = gg.compute_torque(r_eci, q_body, I_sym)

    # Oczekujemy wartości wektora [0, 0, 0] z dokładnością numeryczną
    np.testing.assert_allclose(tau, np.zeros(3), atol=1e-15)


def test_gg_analytical_value():
    gg = GravityGradientDisturbance()

    r_val = 7000000.0
    r_eci = np.array([r_val / np.sqrt(2), r_val / np.sqrt(2), 0.0])
    q_body = np.array([1.0, 0.0, 0.0, 0.0])

    I_sat = np.diag([0.01, 0.02, 0.03])

    tau = gg.compute_torque(r_eci, q_body, I_sat)

    # Obliczenie analityczne przy użyciu mu ze stancji klasy `gg`
    coeff = (3.0 * gg.mu) / (r_val**3)
    expected_tau_z = coeff * 0.5 * (I_sat[1, 1] - I_sat[0, 0])
    expected_tau = np.array([0.0, 0.0, expected_tau_z])

    np.testing.assert_allclose(tau, expected_tau, rtol=1e-7, atol=1e-15)

def test_gg_stabilization_torque():
    """TEST 4: Weryfikacja działania efektu stabilizacji gradientem grawitacji.

    Satelita odchylony od osi Nadir generuje moment przywracający dążący do
    wyrównania osi o najmniejszym momencie bezwładności z pionem lokalnym.
    """
    gg = GravityGradientDisturbance()

    r_val = 7000000.0
    r_eci = np.array([r_val, 0.0, 0.0])

    # Odchylenie o ~5.7 deg wokół osi Z
    angle = np.radians(5.7)
    q_body = np.array([np.cos(angle / 2), 0.0, 0.0, np.sin(angle / 2)])

    # Długa oś satelity to Ix (najmniejsza bezwładność)
    I_sat = np.diag([0.01, 0.02, 0.05])

    tau = gg.compute_torque(r_eci, q_body, I_sat)

    # 1. Moment MUSI być niezerowy
    assert np.linalg.norm(tau) > 0.0

    # 2. Niezerowa składowa na osi Z
    assert abs(tau[2]) > 0.0

    # 3. Transformujemy r_eci do ukł. kadłuba, by sprawdzić składową u y
    r_body = _rotate_vector_by_quaternion(r_eci, q_body)

    assert np.sign(tau[2]) == np.sign(r_body[1])