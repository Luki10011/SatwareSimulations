

from typing import Tuple

from utils.transformations import quaternion_to_euler

import numpy as np

class Gyroscope:
    """
    Model czujnika IMU / żyroskopu mierzącego kąty Eulera oraz prędkość kątową.
    """

    def __init__(
        self,
        noise_std_omega: float = 0.0,   # Odchylenie standardowe szumu prędkości [rad/s]
        bias_omega: np.ndarray = None,   # Dryf/bias [rad/s]
        noise_std_euler: float = 0.0,   # Odchylenie standardowe szumu kątów [deg]
    ):
        self.noise_std_omega = noise_std_omega
        self.bias_omega = bias_omega if bias_omega is not None else np.zeros(3)
        self.noise_std_euler = noise_std_euler

    def read(self, q: np.ndarray, omega: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Zwraca pomiar kątów Eulera [deg] oraz prędkości kątowej [rad/s].
        
        :param q: True kwaternion orientacji [qw, qx, qy, qz]
        :param omega: True prędkość kątowa w ukł. kadłuba [wx, wy, wz] [rad/s]
        :return: (euler_angles_meas [deg], omega_meas [rad/s])
        """
        roll, pitch, yaw = quaternion_to_euler(q, degrees=True)
        euler_meas = np.array([roll, pitch, yaw], dtype=float)

        if self.noise_std_euler > 0:
            euler_meas += np.random.normal(0, self.noise_std_euler, size=3)

        omega_meas = omega + self.bias_omega
        if self.noise_std_omega > 0:
            omega_meas += np.random.normal(0, self.noise_std_omega, size=3)

        return euler_meas, omega_meas