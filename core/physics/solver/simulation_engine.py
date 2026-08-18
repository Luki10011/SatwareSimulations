import copy
from typing import Dict, List, Optional
import numpy as np

from core.physics.control.bdot import BdotController
from core.physics.dataclasses.satellite_configuration import calculate_axisymmetric_cylinder_inertia_tensor
from core.physics.dataclasses.satellite_state import SatelliteState
from core.physics.dataclasses.simulation_state import SimulationState
from core.physics.sensors.gyroscope import Gyroscope
from core.physics.sensors.magnetometer import Magnetometer
from core.physics.solver.solver import equations_of_motion, rk4_step
from utils.transformations import quaternion_to_euler


import copy
from typing import Dict, List, Optional
import numpy as np


class SimulationEngine:

    def __init__(
        self,
        initial_state: SatelliteState,
        I_S: np.ndarray,
        I_R: np.ndarray,
        wheel_axes: List[np.ndarray],
        I_total: np.ndarray,
        rw_max_speed: float,
        dt: float = 0.1,
        sim_date: str = "2020-01-01",
        k_gain : float = 120,
        area : float = 0.3,
        max_current : float = 0.5,
        coil_turns : int = 0,
        dt_mag: float = 1,        
        dt_gyro: float = 1,       
        dt_control: float = 0.8,    
    ):
        self.initial_satellite_state = copy.deepcopy(initial_state)
        self.dt = dt
        self.sim_date = sim_date

        # Częstotliwości/interwały aktualizacji
        self.dt_mag = dt_mag
        self.dt_gyro = dt_gyro
        self.dt_control = dt_control

        # Tensor i macierze bezwładności
        self.I_S = np.array(I_S, dtype=float)
        self.I_R = np.array(I_R, dtype=float)
        self.I_total = np.array(I_total, dtype=float)
        self.I_inv = np.linalg.inv(self.I_S)

        self.wheel_axes = wheel_axes
        self.rw_max_speed = rw_max_speed

        # Transformacja tensora bezwładności dla każdego koła
        self.I_RBS = []
        for axis in self.wheel_axes:
            i_ri_b = calculate_axisymmetric_cylinder_inertia_tensor(
                wheel_tensor=self.I_R, axis=axis
            )
            self.I_RBS.append(i_ri_b)

        self.gyroscope = Gyroscope()
        self.magnetometer = Magnetometer()

        self.bdot_controller = BdotController(
            coil_turns=coil_turns,
            area=area,
            max_current=max_current,
            k_gain=k_gain
        )

        # Stan wewnętrzny i bufory
        self.sim_state: Optional[SimulationState] = None
        self.history: Dict[str, List[float]] = {}

        # Zmienne przechowywania najnowszych odczytów z czujników
        self.current_b_body = np.zeros(3, dtype=float)
        self.current_euler_angles = np.zeros(3, dtype=float)
        self.current_omega = np.zeros(3, dtype=float)

        self.next_mag_update = 0.0
        self.next_gyro_update = 0.0
        self.next_control_update = 0.0

        self.reset()

    def _update_sensors(self) -> None:
        """Dyskretna aktualizacja odczytów czujników."""
        t_curr = self.sim_state.t
        sat = self.sim_state.satellite

        if t_curr >= self.next_mag_update:
            self.current_b_body = self.magnetometer.read(
                date=self.sim_date,
                pos_m=sat.p,
                q=sat.q
            )
            self.next_mag_update += self.dt_mag

        if t_curr >= self.next_gyro_update:
            self.current_euler_angles, self.current_omega = self.gyroscope.read(
                q=sat.q,
                omega=sat.omega
            )
            self.next_gyro_update += self.dt_gyro

        # if t_curr >= self.next_control_update:
        self.i_ctrl = self.bdot_controller.get_control_current(
            current_omega_mes=self.current_omega,
            current_b_mes=self.current_b_body,
            configuration="adaptive"
        )

        self.current_tau_ctrl = self.bdot_controller.get_torque(
            current_applied=self.i_ctrl, 
            current_b_mes=self.current_b_body
        )

        # self.next_control_update += self.dt_control

    def step(self) -> SatelliteState:
        """Wykonuje krok symulacji oraz całowania RK4."""
        # 1. Odświeżenie pomiarów z czujników przed krokiem fizyki
        self._update_sensors()

        # 2. Wykonanie kroku integracji RK4
        y_curr = self.sim_state.satellite.to_vector()
        y_next = rk4_step(
            equations_of_motion,
            self.sim_state.t,
            y_curr,
            self.sim_state.dt,
            self.I_inv,
            self.I_S,
            self.I_RBS,
            self.wheel_axes,
            self.current_tau_ctrl
        )

        # 3. Aktualizacja stanu i czasu
        self.sim_state.satellite = SatelliteState.from_vector(y_next)
        self.sim_state.t += self.sim_state.dt
        self.sim_state.step_count += 1

        self._record_telemetry()
        return self.sim_state.satellite

    def reset(self) -> SatelliteState:
        """Resetuje stan symulacji do t = 0.0 s."""
        self.sim_state = SimulationState(
            t=0.0,
            step_count=0,
            dt=self.dt,
            satellite=copy.deepcopy(self.initial_satellite_state),
        )

        self.next_mag_update = 0.0
        self.next_gyro_update = 0.0
        self.next_control_update = 0.0

        # Pomiary początkowe dla t = 0
        sat = self.sim_state.satellite
        self.current_b_body = self.magnetometer.read(
            date=self.sim_date, pos_m=sat.p, q=sat.q
        )
        self.current_euler_angles, self.current_omega = self.gyroscope.read(
            q=sat.q, omega=sat.omega
        )

        self.i_ctrl = np.zeros(3, dtype=float)
        self.current_tau_ctrl = np.zeros(3, dtype=float)

        self.history = {
            "time": [],
            # --- Pozycja i prędkość ---
            "pos_x": [], "pos_y": [], "pos_z": [],
            "vel_x": [], "vel_y": [], "vel_z": [],
            # --- True State ---
            "roll": [], "pitch": [], "yaw": [],
            "omega_x": [], "omega_y": [], "omega_z": [],
            "q0": [], "q1": [], "q2": [], "q3": [],
            # --- Odczyty czujników ---
            "b_body_x": [], "b_body_y": [], "b_body_z": [],
            "meas_roll": [], "meas_pitch": [], "meas_yaw": [],
            "meas_omega_x": [], "meas_omega_y": [], "meas_omega_z": [],
            # --- Sygnały sterujące (NOWE) ---
            "i_ctrl_x": [], "i_ctrl_y": [], "i_ctrl_z": [],
            "tau_ctrl_x": [], "tau_ctrl_y": [], "tau_ctrl_z": [],
        }

        self._record_telemetry()
        return self.sim_state.satellite

    def _record_telemetry(self) -> None:
        """Zapisuje bieżącą telemetrię fizyczną oraz pomiarową."""
        sat = self.sim_state.satellite
        t = self.sim_state.t

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

        # Odczyty z czujników
        b_micro = self.current_b_body * 1e6
        meas_omega_deg = np.degrees(self.current_omega)

        self.history["b_body_x"].append(b_micro[0])
        self.history["b_body_y"].append(b_micro[1])
        self.history["b_body_z"].append(b_micro[2])

        self.history["meas_roll"].append(self.current_euler_angles[0])
        self.history["meas_pitch"].append(self.current_euler_angles[1])
        self.history["meas_yaw"].append(self.current_euler_angles[2])

        self.history["meas_omega_x"].append(meas_omega_deg[0])
        self.history["meas_omega_y"].append(meas_omega_deg[1])
        self.history["meas_omega_z"].append(meas_omega_deg[2])

        self.history["i_ctrl_x"].append(self.i_ctrl[0])
        self.history["i_ctrl_y"].append(self.i_ctrl[1])
        self.history["i_ctrl_z"].append(self.i_ctrl[2])

        self.history["tau_ctrl_x"].append(self.current_tau_ctrl[0])
        self.history["tau_ctrl_y"].append(self.current_tau_ctrl[1])
        self.history["tau_ctrl_z"].append(self.current_tau_ctrl[2])
