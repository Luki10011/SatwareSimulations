import numpy as np

from core.physics.dataclasses.orbital_data import OrbitalElements
from core.physics.orbits import Orbit


def test_orbit_starts_at_requested_true_anomaly():
    elements = OrbitalElements(
        semi_major_axis=26.6e6,
        eccentricity=0.5,
        inclination=0.0,
        raan=0.0,
        arg_perigee=0.0,
        true_anomaly=np.radians(60.0),
    )

    orbit = Orbit(elements)
    orbit.create_simple_orbit()

    first_position = orbit.orbitalState[0].p
    actual_angle = np.arctan2(first_position[1], first_position[0])

    assert np.isclose(actual_angle, np.radians(60.0), atol=1e-6)
