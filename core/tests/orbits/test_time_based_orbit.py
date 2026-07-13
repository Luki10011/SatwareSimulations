import unittest
import numpy as np

from core.physics.dataclasses.orbital_data import OrbitalElements
from core.physics.orbits import Orbit


class TimeBasedOrbitTests(unittest.TestCase):
    def test_time_based_orbit_uses_orbital_period(self):
        elements = OrbitalElements(
            semi_major_axis=7000.0e3,
            eccentricity=0.2,
            inclination=np.radians(45),
            raan=np.radians(20),
            arg_perigee=np.radians(30),
            true_anomaly=np.radians(180),
        )

        orbit = Orbit(elements)
        orbit.generate_orbit_by_time(num_steps=120)

        self.assertIsNotNone(orbit.orbitalState)
        self.assertEqual(len(orbit.orbitalState), 120)
        self.assertIsNotNone(orbit.orbital_period)
        self.assertGreater(orbit.orbital_period, 0.0)

        initial_position = orbit.initial_position_pqw
        expected_angle = np.radians(180)
        normalized_initial = np.arctan2(np.sin(np.arctan2(initial_position[1], initial_position[0])), np.cos(np.arctan2(initial_position[1], initial_position[0])))
        normalized_expected = np.arctan2(np.sin(expected_angle), np.cos(expected_angle))
        self.assertAlmostEqual(normalized_initial, normalized_expected, places=3)


if __name__ == "__main__":
    unittest.main()
