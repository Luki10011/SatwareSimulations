import copy
import numpy as np

from core.physics.dataclasses.satellite_state import SatelliteState
from core.physics.dataclasses.simulation_state import SimulationState
from core.physics.solver.solver import equations_of_motion, rk4_step
from utils.transformations import quaternion_to_euler


class SimulationEngine:

    def __init__(
        self,
        initial_state: SatelliteState,
        I_matrix: np.ndarray,
        dt: float = 0.1,
    ):
        self.initial_satellite_state = copy.deepcopy(initial_state)
        self.dt = dt
        self.I_inv = np.linalg.inv(I_matrix)

        self.history = {}
        self.sim_state = None
        self.reset()

    def _record_telemetry(self) -> None:
        """Zapisuje aktualny stan do historii telemetrii."""
        sat = self.sim_state.satellite
        t = self.sim_state.t

        # Przeliczenie kwaternionu na kąty Eulera [deg]
        roll, pitch, yaw = quaternion_to_euler(sat.q, degrees=True)
        omega_deg = np.degrees(sat.omega)

        self.history["time"].append(t)
        self.history["pos_x"].append(sat.p[0])
        self.history["pos_y"].append(sat.p[1])
        self.history["pos_z"].append(sat.p[2])

        self.history["vel_x"].append(sat.v[0])
        self.history["vel_y"].append(sat.v[1])
        self.history["vel_z"].append(sat.v[2])

        self.history["roll"].append(roll)
        self.history["pitch"].append(pitch)
        self.history["yaw"].append(yaw)

        self.history["omega_x"].append(omega_deg[0])
        self.history["omega_y"].append(omega_deg[1])
        self.history["omega_z"].append(omega_deg[2])

        self.history["q0"].append(sat.q[0])
        self.history["q1"].append(sat.q[1])
        self.history["q2"].append(sat.q[2])
        self.history["q3"].append(sat.q[3])

    def step(self) -> SatelliteState:
        """Wykonuje jeden krok integracji fizycznej."""
        y_curr = self.sim_state.satellite.to_vector()

        y_next = rk4_step(
            equations_of_motion,
            self.sim_state.t,
            y_curr,
            self.sim_state.dt,
            self.I_inv,
        )

        self.sim_state.satellite = SatelliteState.from_vector(y_next)
        self.sim_state.t += self.sim_state.dt
        self.sim_state.step_count += 1

        self._record_telemetry()
        return self.sim_state.satellite

    def reset(self) -> SatelliteState:
        """Przywraca stan symulacji do początkowego t = 0.0 s."""
        self.sim_state = SimulationState(
            t=0.0,
            step_count=0,
            dt=self.dt,
            satellite=copy.deepcopy(self.initial_satellite_state),
        )

        # Inicjalizacja pustych buforów telemetrii
        self.history = {
            "time": [],
            "pos_x": [],
            "pos_y": [],
            "pos_z": [],
            "vel_x": [],
            "vel_y": [],
            "vel_z": [],
            "roll": [],
            "pitch": [],
            "yaw": [],
            "omega_x": [],
            "omega_y": [],
            "omega_z": [],
            "q0": [],
            "q1": [],
            "q2": [],
            "q3": [],
        }

        # Rejestracja stanu początkowego (t=0)
        self._record_telemetry()
        return self.sim_state.satellite

    def set_initial_conditions(
        self, initial_state: SatelliteState, dt: float = None
    ) -> None:
        self.initial_satellite_state = copy.deepcopy(initial_state)
        if dt is not None:
            self.dt = dt
        self.reset()