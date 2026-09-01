import numpy as np
import pytest
from numpy.testing import assert_allclose

from core.physics.dataclasses.satellite_configuration import calculate_total_inertia_tensor


def test_calculate_total_inertia_empty_wheels():
    i_b = np.diag([10.0, 12.0, 15.0])
    i_s = calculate_total_inertia_tensor(
        mechanical_tensor=i_b,
        wheel_mass=1.0,
        wheel_radius=0.1,
        wheel_height=0.05,
        wheel_axes=[],
        wheel_offsets=[],
    )
    assert_allclose(i_s, i_b, atol=1e-15)


import numpy as np
from numpy.testing import assert_allclose


def test_calculate_total_inertia_default_offset():
    # Kadłub o zerowej masie dla wyizolowania wpływu samego koła
    i_b = np.zeros((3, 3))
    mass = 2.0
    r = 0.01  # promień koła [m]
    h = 0.01  # wysokość koła [m]
    default_d = 0.005  # domyślny nominalny offset 5 mm (0.005 m)

    # Koło zorientowane wzdłuż osi Z
    axis_z = np.array([0.0, 0.0, 1.0])

    # Wywołanie funkcji z wheel_offsets=None (wymuszenie domyślnego offsetu)
    i_s = calculate_total_inertia_tensor(
        mechanical_tensor=i_b,
        wheel_mass=mass,
        wheel_radius=r,
        wheel_height=h,
        wheel_axes=[axis_z],
        wheel_offsets=None,
    )

    # 1. Analityczny tensor bezwładności pojedynczego walca (w układzie lokalnym):
    # I_z = 0.5 * m * r^2
    # I_x = I_y = (1/12) * m * (3*r^2 + h^2)
    i_z_local = 0.5 * mass * (r**2)
    i_x_local = (1.0 / 12.0) * mass * (3 * (r**2) + (h**2))

    # 2. Poprawka Steinera dla przesunięcia r = [0, 0, default_d]:
    # delta_Ixx = m * d^2
    # delta_Iyy = m * d^2
    # delta_Izz = 0 (przesunięcie wzdłuż osi obrotu)
    steiner_xx = mass * (default_d**2)
    steiner_yy = mass * (default_d**2)

    # Oczekiwane wartości końcowe
    expected_ixx = i_x_local + steiner_xx
    expected_iyy = i_x_local + steiner_yy
    expected_izz = i_z_local

    # Weryfikacja
    assert_allclose(i_s[0, 0], expected_ixx, rtol=1e-5)
    assert_allclose(i_s[1, 1], expected_iyy, rtol=1e-5)
    assert_allclose(i_s[2, 2], expected_izz, rtol=1e-5)
    assert_allclose(i_s[0, 1], 0.0, atol=1e-15)  # brak elementów pozaprzekątnych


def test_calculate_total_inertia_physical_invariants():
    i_b = np.diag([5.0, 5.0, 8.0])
    axes = [
        np.array([1.0, 0.0, 0.0]),
        np.array([0.0, 1.0, 0.0]),
        np.array([0.707, 0.707, 0.0]),
    ]
    offsets = [
        np.array([0.1, 0.0, 0.0]),
        np.array([0.0, 0.2, 0.0]),
        np.array([0.05, 0.05, 0.1]),
    ]

    i_s = calculate_total_inertia_tensor(
        mechanical_tensor=i_b,
        wheel_mass=0.5,
        wheel_radius=0.05,
        wheel_height=0.02,
        wheel_axes=axes,
        wheel_offsets=offsets,
    )

    # 1. Symetria
    assert_allclose(i_s, i_s.T, atol=1e-14)

    # 2. Dodatnia określoność (wszystkie wartości własne > 0)
    eigenvalues = np.linalg.eigvalsh(i_s)
    assert np.all(eigenvalues > 0)

    # 3. Nierówność trójkąta
    ixx, iyy, izz = i_s[0, 0], i_s[1, 1], i_s[2, 2]
    assert ixx + iyy > izz
    assert ixx + izz > iyy
    assert iyy + izz > ixx


def test_analytical_values():

    i_b = np.diag(
        [1/6, 1/6, 1/15]
    )

    i_s = calculate_total_inertia_tensor(
        mechanical_tensor=i_b,
        wheel_mass=0.5,
        wheel_radius=0.05,
        wheel_height=0.02,
        wheel_axes=[np.array([1, 0, 0])],
        wheel_offsets=None,
    )

    expected_ixx = 0.16729167
    expected_iyy = 0.16700833
    expected_izz = 0.06700833

    assert_allclose(i_s[0, 0], expected_ixx, rtol=1e-5)
    assert_allclose(i_s[1, 1], expected_iyy, rtol=1e-5)
    assert_allclose(i_s[2, 2], expected_izz, rtol=1e-5)
