from datetime import datetime
from typing import Optional
import numpy as np
import ppigrf
from utils.rotations import euler_321_to_rotation_matrix, quaternion_to_rotation_matrix


class Magnetometer:
    """
    Model czujnika magnetometru mierzącego wektor pola magnetycznego w ukł. kadłuba satelity.
    """

    def __init__(
        self,
        noise_std_tesla: float = 0.0,       
        bias_tesla: Optional[np.ndarray] = None  # Offset / bias czujnika [Tesla]
    ):
        self.noise_std = noise_std_tesla
        self.bias = bias_tesla if bias_tesla is not None else np.zeros(3, dtype=float)

    def get_magnetic_field_in_eci_frame(self,
        date: str,
        pos_m: np.ndarray) -> np.ndarray:

        x, y, z = pos_m
        rho = np.linalg.norm(pos_m)
        if rho == 0:
            return np.zeros(3)

        phi_e = 0.0
        theta_e = np.arccos(z / rho)
        psi_e = np.arctan2(y, x)

        latitude_deg = 90.0 - np.degrees(theta_e)
        longitude_deg = np.degrees(psi_e)
        rho_km = rho / 1000.0
        h_km = rho_km - 6371.0  # Wysokość nad elipsoidą/powierzchnią Ziemi [km]

        date_dt = datetime.strptime(date, "%Y-%m-%d")
        Be, Bn, Bu = ppigrf.igrf(longitude_deg, latitude_deg, h_km, date_dt)

        bn = Bn.item()
        be = Be.item()
        bd = Bu.item()  # Down = -Up

        b_ned = np.array([bn, be, -bd])

        t_ib = euler_321_to_rotation_matrix(phi_e, theta_e + np.pi, psi_e)
        b_eci = t_ib @ b_ned

        return b_eci * 1e-9

    def get_magnetic_field_in_body_frame(self,
        date: str,
        pos_m: np.ndarray,
        q: np.ndarray
    ) -> np.ndarray:
        """
        Oblicza wektor pola magnetycznego Ziemi w układzie kadłuba satelity [T].

        :param date: Data w formacie YYYY-MM-DD
        :param pos_m: Pozycja satelity w układzie inercjalnym [x, y, z] w metrach
        :param q: Kwaternion orientacji satelity [qw, qx, qy, qz]
        :return: Wektor pola B w układzie kadłuba w Teslach [T]
        """
        x, y, z = pos_m
        rho = np.linalg.norm(pos_m)
        if rho == 0:
            return np.zeros(3)

        phi_e = 0.0
        theta_e = np.arccos(np.clip(z / rho, -1.0, 1.0))
        psi_e = np.arctan2(y, x)

        latitude_deg = 90.0 - np.degrees(theta_e)
        longitude_deg = np.degrees(psi_e)
        rho_km = rho / 1000.0
        h_km = rho_km - 6371.0  # Wysokość nad elipsoidą/powierzchnią Ziemi [km]

        date_dt = datetime.strptime(date, "%Y-%m-%d")
        Be, Bn, Bu = ppigrf.igrf(longitude_deg, latitude_deg, h_km, date_dt)

        bn = Bn.item()
        be = Be.item()
        bd = Bu.item()  # Down = -Up

        b_ned = np.array([bn, be, -bd])

        t_ib = euler_321_to_rotation_matrix(phi_e, theta_e + np.pi, psi_e)
        b_eci = t_ib @ b_ned

        r_body2eci = quaternion_to_rotation_matrix(q)
        b_body_nt = r_body2eci.T @ b_eci

        return b_body_nt * 1e-9



    def read(self, date: str, pos_m: np.ndarray, q: np.ndarray) -> np.ndarray:
        """
        Zwraca pomiar pola magnetycznego w układzie kadłuba [T].

        :param date: Data w formacie YYYY-MM-DD
        :param pos_m: True pozycja satelity [x, y, z] w metrach
        :param q: True kwaternion orientacji [qw, qx, qy, qz]
        :return: Pomiar pola B [T] z ew. szumem i biasem
        """
        b_true = self.get_magnetic_field_in_body_frame(date=date, pos_m=pos_m, q=q)

        b_meas = b_true + self.bias
        if self.noise_std > 0:
            b_meas += np.random.normal(0.0, self.noise_std, size=3)

        return b_meas