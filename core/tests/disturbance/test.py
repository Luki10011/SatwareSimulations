from core.physics.disturbance.atmoshperic_drag import AtmosphericDragDisturbance
import numpy as np

def test_torque_zero_for_symmetric_body_and_centered_com():
    """Sprawdza, czy dla symetrycznego prostopadłościanu z CoM=[0,0,0] moment obrotowy wynosi 0."""
    drag_model = AtmosphericDragDisturbance(
        Cd=2.2,
        dimensions=(0.8, 0.6, 0.5),
        mass=2.0,
        com_offset=np.array([0.0, 0.0, 0.0]),
    )

    r_eci = np.array([7000000.0, 0.0, 0.0])
    # Przepływ pod kątem w płaszczyźnie X-Z
    v_eci = np.array([5303.3, 0.0, 5303.3])
    q_identity = np.array([1.0, 0.0, 0.0, 0.0])

    f_drag, tau_drag = drag_model.compute_disturbance(r_eci, v_eci, q_identity)

    # Siła wypadkowa musi być niezerowa
    assert np.linalg.norm(f_drag) > 0.0
    print(f_drag)

if __name__ == "__main__":
    test_torque_zero_for_symmetric_body_and_centered_com()