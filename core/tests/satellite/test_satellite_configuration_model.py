import numpy as np

from core.physics.dataclasses.satellite_configuration import (
    build_satellite_configuration,
    calculate_reaction_wheel_inertia_tensor,
    calculate_total_inertia_tensor,
    validate_satellite_configuration_data,
)


def test_valid_principal_wheel_configuration_is_accepted():
    data = {
        "mechanical": {
            "mass": 12.5,
            "dimensions": [0.3, 0.2, 0.1],
            "inertia_tensor": [[0.2, 0.0, 0.0], [0.0, 0.15, 0.0], [0.0, 0.0, 0.1]],
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

    assert validate_satellite_configuration_data(data) == []
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
    assert any("reaction wheels" in error.lower() for error in errors)


def test_reaction_wheel_inertia_tensor_includes_steiner_correction():
    wheel_tensor = calculate_reaction_wheel_inertia_tensor(0.25, 0.05, 0.02)
    assert wheel_tensor.shape == (3, 3)
    assert wheel_tensor[0, 0] > 0.0
    assert wheel_tensor[2, 2] > wheel_tensor[0, 0]

    mechanical_tensor = np.array([[0.02, 0.0, 0.0], [0.0, 0.015, 0.0], [0.0, 0.0, 0.01]])
    total_tensor = calculate_total_inertia_tensor(
        mechanical_tensor=mechanical_tensor,
        mechanical_mass=12.5,
        wheel_mass=0.25,
        wheel_radius=0.05,
        wheel_height=0.02,
        wheel_count=3,
        com_offset=np.array([0.003, 0.002, 0.001]),
    )

    assert total_tensor.shape == (3, 3)
    assert total_tensor[0, 0] > mechanical_tensor[0, 0]
    assert total_tensor[1, 1] > mechanical_tensor[1, 1]
    assert total_tensor[2, 2] > mechanical_tensor[2, 2]
