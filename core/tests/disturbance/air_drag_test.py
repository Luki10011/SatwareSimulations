import numpy as np
import pytest
from core.physics.disturbance.atmoshperic_drag import AtmosphericDragDisturbance


@pytest.fixture
def drag_model():
    """Tworzy instancję oporu dla satelity 0.8m x 0.6m x 0.5m o masie 2kg."""
    return AtmosphericDragDisturbance(
        Cd=2.2,
        dimensions=(0.8, 0.6, 0.5),
        mass=2.0,
        com_offset=np.array([0.0, 0.0, 0.0]),
    )


def test_drag_force_opposite_to_velocity(drag_model):
    """Sprawdza, czy przyspieszenie oporu działa idealnie naprzeciw wektora prędkości względnej."""
    r_eci = np.array([7000000.0, 0.0, 0.0])  # ~622 km wysokości
    v_eci = np.array([0.0, 7500.0, 0.0])
    q_identity = np.array([1.0, 0.0, 0.0, 0.0])

    a_drag, _ = drag_model.compute_disturbance(r_eci, v_eci, q_identity)

    # V_rel uwzględnia rotację Ziemi, więc v_rel_x = 0, v_rel_y = 7500 - omega*r, v_rel_z = 0
    v_rel = v_eci - np.cross(drag_model.omega_e_vec, r_eci)
    u_v_rel = v_rel / np.linalg.norm(v_rel)

    # Przyspieszenie powinno mieć zwrot przeciwny do u_v_rel
    u_a_drag = a_drag / np.linalg.norm(a_drag)
    np.testing.assert_allclose(u_a_drag, -u_v_rel, atol=1e-6)


def test_projected_area_principal_axes(drag_model):
    """Sprawdza wyznaczanie powierzchni natarcia dla przepływu wzdłuż osi X, Y, Z."""
    # Ściana X: dy * dz = 0.6 * 0.5 = 0.3 m^2
    area_x, cop_x = drag_model._compute_area_and_cop(np.array([1.0, 0.0, 0.0]))
    assert pytest.approx(area_x) == 0.3
    np.testing.assert_allclose(cop_x, [0.4, 0.0, 0.0])

    # Ściana Y: dx * dz = 0.8 * 0.5 = 0.4 m^2
    area_y, cop_y = drag_model._compute_area_and_cop(np.array([0.0, -1.0, 0.0]))
    assert pytest.approx(area_y) == 0.4
    np.testing.assert_allclose(cop_y, [0.0, -0.3, 0.0])

    # Ściana Z: dx * dy = 0.8 * 0.6 = 0.48 m^2
    area_z, cop_z = drag_model._compute_area_and_cop(np.array([0.0, 0.0, 1.0]))
    assert pytest.approx(area_z) == 0.48
    np.testing.assert_allclose(cop_z, [0.0, 0.0, 0.25])


def test_torque_generation_with_com_offset():
    """Sprawdza generowanie momentu obrotowego przy nietrywialnym offsetcie środka masy."""
    com_offset = np.array([0.05, 0.0, 0.0])  # CoM przesunięty o +5 cm w osi X
    drag_model_offset = AtmosphericDragDisturbance(
        Cd=2.2,
        dimensions=(0.8, 0.6, 0.5),
        mass=2.0,
        com_offset=com_offset,
    )

    r_eci = np.array([7000000.0, 0.0, 0.0])
    v_eci = np.array([0.0, 0.0, 7500.0])  # Przepływ trafia w ścianę +Z (u_v_body = [0, 0, 1])
    q_identity = np.array([1.0, 0.0, 0.0, 0.0])

    _, tau_drag = drag_model_offset.compute_disturbance(r_eci, v_eci, q_identity)

    # Dla przepływu w osi +Z: CoP = [0, 0, 0.25]
    # Ramię siły r_arm = CoP - CoM = [-0.05, 0, 0.25]
    # Siła F_body skierowana w -Z ([0, 0, -F_mag])
    # Moment tau = r_arm x F_body -> powinen dać składową w osi Y!
    assert tau_drag[1] != 0.0
    assert pytest.approx(tau_drag[0]) == 0.0
    assert pytest.approx(tau_drag[2]) == 0.0


def test_zero_velocity_handling(drag_model):
    """Sprawdza brak błędów (np. dzielenia przez zero) dla zerowej prędkości."""
    r_eci = np.array([7000000.0, 0.0, 0.0])
    v_eci = np.cross(drag_model.omega_e_vec, r_eci)  # V_rel = 0
    q_identity = np.array([1.0, 0.0, 0.0, 0.0])

    a_drag, tau_drag = drag_model.compute_disturbance(r_eci, v_eci, q_identity)

    np.testing.assert_allclose(a_drag, np.zeros(3))
    np.testing.assert_allclose(tau_drag, np.zeros(3))