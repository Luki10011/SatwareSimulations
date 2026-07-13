import numpy as np

from core.physics.dataclasses.orbital_data import OrbitalElements
from core.physics.orbits import Orbit


def test_speed_profile_is_faster_at_perigee_than_apogee():
    elements = OrbitalElements(
        semi_major_axis=26.6e6,
        eccentricity=0.72,
        inclination=np.radians(63.4),
        raan=np.radians(0.0),
        arg_perigee=np.radians(270.0),
        true_anomaly=0.0,
    )

    orbit = Orbit(elements)
    orbit.create_simple_orbit()

    speed_profile = orbit.get_speed_profile()

    assert speed_profile is not None
    assert len(speed_profile) > 10
    assert np.max(speed_profile) > np.min(speed_profile)

    positions = np.array([state.p for state in orbit.orbitalState], dtype=float)
    radii = np.linalg.norm(positions, axis=1)
    perigee_idx = int(np.argmin(radii))
    apogee_idx = int(np.argmax(radii))

    assert speed_profile[perigee_idx] > speed_profile[apogee_idx]
