import copy
from typing import Dict, List, Optional, Tuple
import numpy as np

from core.physics.control.bdot import BdotController
from core.physics.control.rw_controller import ReactionWheelsController
from core.physics.control.slerp_trajectory import SlerpTrajectoryGenerator
from core.physics.dataclasses.satellite_configuration import (
    calculate_axisymmetric_cylinder_inertia_tensor,
)
from core.physics.dataclasses.satellite_state import SatelliteState
from core.physics.dataclasses.simulation_state import SimulationState
from core.physics.sensors.gyroscope import Gyroscope
from core.physics.sensors.magnetometer import Magnetometer
from core.physics.solver.solver import equations_of_motion, rk4_step
from utils.transformations import euler_to_quaternion, quaternion_to_euler


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
        sim_date: str = "2026-01-01",
        k_gain: float = 7200,
        area: float = 0.3,
        max_current: float = 0.5,
        coil_turns: int = 0,
        dt_mag: float = 0.4,
        dt_gyro: float = 0.4,
        dt_control: float = 0.01,
        kp_rw: float =  0.003333,
        kd_rw: float = 45* 0.003333,
        aligned_axes: bool = False,
    ):
        self.initial_satellite_state = copy.deepcopy(initial_state)
        self.dt = dt
        self.sim_date = sim_date

        self.dt_mag = dt_mag
        self.dt_gyro = dt_gyro
        self.dt_control = dt_control

        self.I_S = np.array(I_S, dtype=float)
        self.I_R = np.array(I_R, dtype=float)
        self.I_total = np.array(I_total, dtype=float)
        self.I_inv = np.linalg.inv(self.I_total)

        self.wheel_axes = wheel_axes
        self.rw_max_speed = rw_max_speed

        self.kd = kd_rw
        self.kp = kp_rw

        # Pobranie momentu bezwładności koła wokół osi obrotu Z_R
        self.I_R_spin = float(self.I_R[2, 2]) if self.I_R.ndim == 2 else float(self.I_R)

        # ADCS state
        self.adcs_mode: str = "IDLE"
        self.detumble_algorithm: str = "normal"
        self.target_angles: Tuple[float, float, float] = (0.0, 0.0, 0.0)
        self.mode_summary: str = "Mode: IDLE"

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
            k_gain=k_gain,
        )

        # Kontroler kół reakcyjnych
        self.rw_controller = ReactionWheelsController(
            wheel_axes=self.wheel_axes,
            I_R_spin=self.I_R_spin,
            kp=kp_rw,
            kd=kd_rw,
            aligned_axes=aligned_axes,
            I_total=self.I_total,
            max_speed=self.rw_max_speed
        )

        self.slerp_gen = SlerpTrajectoryGenerator(
            max_slew_rate_deg_s=2.0
        )  # Domyślnie 2 deg/s
        self.last_target_angles: Optional[List[float]] = None
        self.last_adcs_mode: str = self.adcs_mode
        

        self.sim_state: Optional[SimulationState] = None
        self.history: Dict[str, List[float]] = {}

        self.current_b_body = np.zeros(3, dtype=float)
        self.current_euler_angles = np.zeros(3, dtype=float)
        self.current_omega = np.zeros(3, dtype=float)

        self.alpha_wheels = np.zeros(len(self.wheel_axes), dtype=float)
        self.current_tau_ctrl = np.zeros(3, dtype=float)
        self.i_ctrl = np.zeros(3, dtype=float)

        self.next_mag_update = 0.0
        self.next_gyro_update = 0.0
        self.next_control_update = 0.0

        self.reset()

    def set_adcs_mode(
        self,
        mode: str,
        detumble_algorithm: str = "normal",
        target_angles: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        k_gain: Optional[float] = None,
        kp_rw: Optional[float] = None,
        kd_rw: Optional[float] = None,
    ) -> str:
        self.adcs_mode = mode
        self.detumble_algorithm = detumble_algorithm
        self.target_angles = target_angles

        if k_gain is not None:
            self.bdot_controller.k_gain = k_gain

        if kp_rw is not None and kd_rw is not None:
            self.rw_controller.set_gains(kp=kp_rw, kd=kd_rw)

        if self.adcs_mode == "DETUMBLE":
            algo_name = "Adaptive B-Dot" if self.detumble_algorithm == "adaptive" else "Normal B-Dot"
            self.mode_summary = f"Mode: DETUMBLE | Algo: {algo_name} | Gain k: {self.bdot_controller.k_gain:.1f}"
        elif self.adcs_mode == "POINTING":
            r, p, y = self.target_angles
            self.mode_summary = f"Mode: POINTING | Target: Roll={r:.1f}°, Pitch={p:.1f}°, Yaw={y:.1f}°"
        else:
            self.mode_summary = "Mode: IDLE | ADCS active control disabled"

        print(self.mode_summary)
        print(f"Raction Wheels max speed [rad/s]: {self.rw_max_speed}")
        return self.mode_summary

    def _update_sensors(self) -> None:
        t_curr = self.sim_state.t
        sat = self.sim_state.satellite

        if t_curr >= self.next_mag_update:
            self.current_b_body = self.magnetometer.read(
                date=self.sim_date, pos_m=sat.p, q=sat.q
            )
            self.next_mag_update += self.dt_mag

        if t_curr >= self.next_gyro_update:
            self.current_euler_angles, self.current_omega = self.gyroscope.read(
                q=sat.q, omega=sat.omega
            )
            self.next_gyro_update += self.dt_gyro

        if t_curr >= self.next_control_update:
            if self.adcs_mode == "DETUMBLE":
                self.alpha_wheels = np.zeros(len(self.wheel_axes))
                self.i_ctrl = self.bdot_controller.get_control_current(
                    current_omega_mes=self.current_omega,
                    current_b_mes=self.current_b_body,
                    configuration=self.detumble_algorithm,
                )
                self.current_tau_ctrl = self.bdot_controller.get_torque(
                    current_applied=self.i_ctrl,
                    current_b_mes=self.current_b_body,
                )

            elif self.adcs_mode == "POINTING":
                self.i_ctrl = np.zeros(3)

                current_quat = np.asarray(
                    self.sim_state.satellite.q,
                    dtype=float,
                ).copy()

                current_quat /= np.linalg.norm(current_quat)

                final_target_quat = euler_to_quaternion(
                    *self.target_angles,
                    degrees=True,
                )

                final_target_quat = np.asarray(
                    final_target_quat,
                    dtype=float,
                )

                final_target_quat /= np.linalg.norm(
                    final_target_quat
                )

                current_target_list = list(
                    self.target_angles
                )

                if (
                    self.last_target_angles is None
                    or self.last_target_angles != current_target_list
                ):
                    self.slerp_gen.set_new_target(
                        q_current=current_quat,
                        q_target=final_target_quat,
                        t_curr=self.sim_state.t,
                    )

                    self.last_target_angles = current_target_list

                cmd_quat, cmd_omega = (
                    self.slerp_gen.get_command(
                        self.sim_state.t
                    )
                )

                self.alpha_wheels, self.current_tau_ctrl = (
                    self.rw_controller.compute_control(
                        current_quat=current_quat,
                        target_quat=cmd_quat,
                        current_omega=self.current_omega,
                        current_omega_rw=self.sim_state.satellite.omega_rw,
                        target_omega=cmd_omega,
                    )
                )

            else:  # IDLE
                self.i_ctrl = np.zeros(3)
                self.alpha_wheels = np.zeros(len(self.wheel_axes))
                self.current_tau_ctrl = np.zeros(3)

            self.next_control_update += self.dt_control

    def step(self) -> SatelliteState:
        self._update_sensors()

        y_curr = self.sim_state.satellite.to_vector()
        y_next = rk4_step(
            equations_of_motion,
            self.sim_state.t,
            y_curr,
            self.sim_state.dt,
            self.I_inv,
            self.I_S,
            self.wheel_axes,
            self.current_tau_ctrl,
            self.alpha_wheels,
            self.I_R_spin,
        )

        self.sim_state.satellite = SatelliteState.from_vector(y_next)
        self.sim_state.t += self.sim_state.dt
        self.sim_state.step_count += 1

        self._record_telemetry()
        return self.sim_state.satellite

    def reset(self) -> SatelliteState:
        """Resetuje stan symulacji do t = 0.0 s oraz czyści stan regulatorów."""
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

        # Reset stanu ADCS
        self.adcs_mode = "IDLE"
        self.detumble_algorithm = "normal"
        self.target_angles = (0.0, 0.0, 0.0)

        self.history = {
            "time": [],
            # --- Pozycja i prędkość ---
            "pos_x": [],
            "pos_y": [],
            "pos_z": [],
            "vel_x": [],
            "vel_y": [],
            "vel_z": [],
            # --- True State ---
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
            # --- Odczyty czujników ---
            "b_body_x": [],
            "b_body_y": [],
            "b_body_z": [],
            "meas_roll": [],
            "meas_pitch": [],
            "meas_yaw": [],
            "meas_omega_x": [],
            "meas_omega_y": [],
            "meas_omega_z": [],
            # --- Sygnały sterujące ---
            "i_ctrl_x": [],
            "i_ctrl_y": [],
            "i_ctrl_z": [],
            "tau_ctrl_x": [],
            "tau_ctrl_y": [],
            "tau_ctrl_z": [],
            # --- reaction wheels ---
            "omega_rw_x" : [],
            "omega_rw_y" : [],
            "omega_rw_z" : [],
            "alpha_x" : [],
            "alpha_y" : [],
            "alpha_z" : [],
        }

        self._record_telemetry()
        return self.sim_state.satellite

    def _record_telemetry(self) -> None:
        """Zapisuje bieżącą telemetrię fizyczną oraz pomiarową."""
        sat = self.sim_state.satellite
        t = self.sim_state.t

        roll, pitch, yaw = quaternion_to_euler(sat.q, degrees=True)
        omega_deg = np.degrees(sat.omega)
        omega_rw_deg = np.degrees(sat.omega_rw)

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

        self.history["omega_rw_x"].append(omega_rw_deg[0])
        self.history["omega_rw_y"].append(omega_rw_deg[1])
        self.history["omega_rw_z"].append(omega_rw_deg[2])

        self.history["alpha_x"].append(self.alpha_wheels[0])
        self.history["alpha_y"].append(self.alpha_wheels[1])
        self.history["alpha_z"].append(self.alpha_wheels[2])