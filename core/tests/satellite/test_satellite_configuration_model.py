import numpy as np

from core.physics.dataclasses.satellite_configuration import (
    build_satellite_configuration,
    calculate_reaction_wheel_inertia_tensor,
    calculate_total_inertia_tensor,
    reaction_wheel_axes,
    validate_satellite_configuration_data,
)


def test_valid_principal_wheel_configuration_is_accepted():
    data = {
        "mechanical": {
            "mass": 12.5,
            "dimensions": [0.3, 0.2, 0.1],
            "inertia_tensor": [[0.06, 0.0, 0.0], [0.0, 0.12, 0.0], [0.0, 0.0, 0.14]],
        },
        "electromagnetic": {
            "coil_turns": 120,
            "coil_area": 0.04,
            "max_current": 2.5,
        },
        "reaction_wheels": {
            "configuration": "principal",
            "wheel_count": 3,
            "wheel_mass": 0.25,
            "wheel_radius": 0.05,
            "wheel_height": 0.02,
            "wheel_max_speed": 6000,
        },
    }

    errors = validate_satellite_configuration_data(data)
    assert not errors
    config = build_satellite_configuration(data)
    assert config.mechanical.m == 12.5
    assert config.reaction_wheels.configuration == "principal"


def test_invalid_non_principal_wheel_configuration_is_rejected():
    data = {
        "mechanical": {
            "mass": 10.0,
            "dimensions": [0.2, 0.2, 0.2],
            "inertia_tensor": [[0.1, 0.0, 0.0], [0.0, 0.1, 0.0], [0.0, 0.0, 0.1]],
        },
        "electromagnetic": {
            "coil_turns": 100,
            "coil_area": 0.03,
            "max_current": 2.0,
        },
        "reaction_wheels": {
            "configuration": "pyramid",
            "wheel_count": 3,
            "wheel_mass": 0.2,
            "wheel_radius": 0.04,
            "wheel_height": 0.015,
            "wheel_max_speed": 5000,
        },
    }

    errors = validate_satellite_configuration_data(data)
    assert errors
    assert any(
        "wheel count" in error.lower() or "reaction wheel" in error.lower()
        for error in errors.values()
    )


def test_reaction_wheel_inertia_tensor_includes_steiner_correction():
    wheel_tensor = calculate_reaction_wheel_inertia_tensor(0.25, 0.05, 0.02)
    assert wheel_tensor.shape == (3, 3)
    assert wheel_tensor[0, 0] > 0.0
    assert wheel_tensor[2, 2] > wheel_tensor[0, 0]

    mechanical_tensor = np.array([[0.02, 0.0, 0.0], [0.0, 0.015, 0.0], [0.0, 0.0, 0.01]])
    wheel_axes = [
        np.array([1.0, 0.0, 0.0], dtype=float),
        np.array([0.0, 1.0, 0.0], dtype=float),
        np.array([0.0, 0.0, 1.0], dtype=float),
    ]
    total_tensor = calculate_total_inertia_tensor(
        mechanical_tensor=mechanical_tensor,
        wheel_mass=0.25,
        wheel_radius=0.05,
        wheel_height=0.02,
        wheel_axes=wheel_axes,
    )

    assert total_tensor.shape == (3, 3)
    assert total_tensor[0, 0] > mechanical_tensor[0, 0]
    assert total_tensor[1, 1] > mechanical_tensor[1, 1]
    assert total_tensor[2, 2] > mechanical_tensor[2, 2]


def test_reaction_wheel_axes_principal_and_pyramid_layouts():
    principal_axes = reaction_wheel_axes("principal", 3)
    assert len(principal_axes) == 3
    assert np.allclose(principal_axes[0], [1.0, 0.0, 0.0])
    assert np.allclose(principal_axes[1], [0.0, 1.0, 0.0])
    assert np.allclose(principal_axes[2], [0.0, 0.0, 1.0])

    pyramid_axes = reaction_wheel_axes("pyramid", 4)
    assert len(pyramid_axes) == 4
    for axis in pyramid_axes:
        assert np.isclose(np.linalg.norm(axis), 1.0)
