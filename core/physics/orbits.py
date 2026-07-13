from core.physics.dataclasses.orbital_data import OrbitalElements, OrbitalStateVector
from utils.configuration import dt
from typing import List
from utils.constants import CONSTANTS
from utils.rotations import rotate_pqw_to_eci
import copy

import numpy as np
import logging


class Orbit:
    def __init__(self, orbitalElements: OrbitalElements) -> None:
        self.orbitalElements = orbitalElements
        self.orbitalState: np.ndarray[OrbitalStateVector] = None
        self.orbitalState_PQW : np.ndarray[OrbitalStateVector] = None
        self.perigee = None
        self.apogee = None
        self.dt = dt
        self.logger = logging.getLogger(__name__)
        self.initial_position_pqw = None
        self.orbital_period = None

    """
        This function is used for generating simple trajectory based on
        given orbital elements and inital conditions (position). Inital
        velocity will be calculted based on the equations.
    """
    def create_simple_orbit(self):
        self.generate_orbit_by_time()
        self.logger.info("Orbit state calculated successfully.")

    def generate_orbit_by_time(self, num_steps: int = 2_000, duration: float | None = None):
        """Generate orbital states sampled uniformly in time over one orbital period."""
        a = self.orbitalElements.semi_major_axis
        e = self.orbitalElements.eccentricity
        mu = CONSTANTS["mu"]

        if duration is None:
            self.orbital_period = 2 * np.pi * np.sqrt(a**3 / mu)
            duration = self.orbital_period

        if e == 0.0:
            self._calculate_circular_orbit_PQW(num_steps=num_steps, period=duration)
        else:
            self._calculate_eliptical_orbit_PQW(e, num_steps=num_steps, period=duration)

        self.orbitalState_PQW = copy.deepcopy(self.orbitalState)
        self._convert_from_PQW_to_ECI()
        return self.orbitalState
    
    def _calculate_eliptical_orbit_PQW(self, e, num_steps=2_500, period: float | None = None):
        a = self.orbitalElements.semi_major_axis
        mu = CONSTANTS["mu"]

        # calculating specific angular momentum (h) based on the semi major axis and gravitational parameter
        h = np.sqrt(mu * a * (1 - e**2))
        if period is None:
            period = 2 * np.pi * np.sqrt(a**3 / mu)
        self.orbital_period = period

        times = np.linspace(0.0, period, num_steps)
        self.orbitalState = np.empty(num_steps, dtype=object)

        initial_nu = np.mod(self.orbitalElements.true_anomaly, 2 * np.pi)
        initial_E = self._true_anomaly_to_eccentric_anomaly(initial_nu, e)
        initial_M = initial_E - e * np.sin(initial_E)
        mean_motion = 2 * np.pi / period

        for idx, t in enumerate(times):
            M = np.mod(initial_M + mean_motion * t, 2 * np.pi)
            E = self._solve_kepler_equation(M, e)
            nu = self._eccentric_anomaly_to_true_anomaly(E, e)
            nu = np.mod(nu, 2 * np.pi)

            r_mag = (h**2 / mu) / (1 + e * np.cos(nu))
            r_pqw = np.array([r_mag * np.cos(nu), r_mag * np.sin(nu), 0])
            v_pqw = np.array([
                -(mu / h) * np.sin(nu),
                (mu / h) * (e + np.cos(nu)),
                0
            ])
            self.orbitalState[idx] = OrbitalStateVector(p=r_pqw, v=v_pqw)

        self.initial_position_pqw = self.orbitalState[0].p.copy()

    
    def get_ascending_node_line(self):
        if self.orbitalState is not None:
            # Calculate the ascending node line in ECI frame
            r_eci = self.orbitalState[0].p  # Position vector in ECI frame
            v_eci = self.orbitalState[0].v  # Velocity vector in ECI frame
            
            # Calculate the ascending node line as the cross product of position and velocity
            h = np.cross(r_eci, v_eci)
            ascending_node_line = np.cross(np.array([0, 0, 1]), h)

            return ascending_node_line
        return None

    def get_perigee_line(self):
        if self.orbitalState is not None:
            positions = np.array([state.p for state in self.orbitalState])
            
            distances = np.linalg.norm(positions, axis=1)
            
            perigee_idx = np.argmin(distances)
            
            self.perigee = positions[perigee_idx]
            return self.perigee
            
        return None

    def get_true_anomaly_vector(self):
        """Return the current orbital position vector for the selected true anomaly in ECI frame."""
        if self.orbitalState is None:
            return None

        initial_state = self.orbitalState[0]
        return initial_state.p.copy()

    def get_speed_profile(self):
        """Return the orbital speed at each propagated state in m/s."""
        if self.orbitalState is None:
            return None

        speeds = []
        for state in self.orbitalState:
            velocity_magnitude = np.linalg.norm(state.v)
            speeds.append(float(velocity_magnitude))

        return np.array(speeds, dtype=np.float32)
        
    def _calculate_circular_orbit_PQW(self, num_steps=2_500, period: float | None = None):
        """
            This function is used for calculating the orbit state in PQW frame
        """
        a = self.orbitalElements.semi_major_axis
        mu = CONSTANTS["mu"]
        if period is None:
            period = 2 * np.pi * np.sqrt(a**3 / mu)
        self.orbital_period = period

        self.orbitalState = np.zeros(num_steps, dtype=object)
        r = a
        v = np.sqrt(mu / r)

        times = np.linspace(0.0, period, num_steps)
        initial_nu = self.orbitalElements.true_anomaly
        for idx, t in enumerate(times):
            mean_motion = 2 * np.pi / period
            nu = np.mod(initial_nu + mean_motion * t, 2 * np.pi)
            r_pqw = np.array([r * np.cos(nu), r * np.sin(nu), 0])
            v_pqw = np.array([-v * np.sin(nu), v * np.cos(nu), 0])
            self.orbitalState[idx] = OrbitalStateVector(p=r_pqw, v=v_pqw)

        self.initial_position_pqw = self.orbitalState[0].p.copy()
        self.logger.info("Circular orbit in PQW frame calculated successfully.")

    def _solve_kepler_equation(self, M: float, e: float, tol: float = 1e-12, max_iter: int = 100) -> float:
        """Solve Kepler's equation for eccentric anomaly using Newton-Raphson."""
        E = M if e < 0.8 else np.pi
        for _ in range(max_iter):
            f = E - e * np.sin(E) - M
            fp = 1 - e * np.cos(E)
            delta = f / fp
            E -= delta
            if abs(delta) < tol:
                break
        return E

    def _true_anomaly_to_eccentric_anomaly(self, nu: float, e: float) -> float:
        """Convert true anomaly to eccentric anomaly for an elliptical orbit."""
        return 2 * np.arctan2(np.sqrt(1 - e) * np.sin(nu / 2), np.sqrt(1 + e) * np.cos(nu / 2))

    def _eccentric_anomaly_to_true_anomaly(self, E: float, e: float) -> float:
        """Convert eccentric anomaly to true anomaly for an elliptical orbit."""
        return 2 * np.arctan2(np.sqrt(1 + e) * np.sin(E / 2), np.sqrt(1 - e) * np.cos(E / 2))


    def _convert_from_PQW_to_ECI(self):
        """
            This function is used for converting the calculated state from PQW frame to ECI frame
        """
        for state in self.orbitalState:
            state.p = rotate_pqw_to_eci(state.p, self.orbitalElements.raan, self.orbitalElements.inclination, self.orbitalElements.arg_perigee)
            state.v = rotate_pqw_to_eci(state.v, self.orbitalElements.raan, self.orbitalElements.inclination, self.orbitalElements.arg_perigee)


    
        
