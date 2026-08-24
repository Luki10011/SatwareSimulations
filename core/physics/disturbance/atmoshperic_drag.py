from datetime import datetime, timezone
import numpy as np
from pymsis import Variable

from utils.rotations import quaternion_to_rotation_matrix

try:
    from pymsis import msis
    HAS_PYMSIS = True
except ImportError:
    HAS_PYMSIS = False


from utils.constants import CONSTANTS

class AtmosphericDragDisturbance:
    """Modeluje siłę i moment oporu atmosferycznego LEO z wykorzystaniem
    modelu NRLMSISE-00 (poprzez pymsis) oraz geometrii prostopadłościanu.
    """

    def __init__(
        self,
        Cd: float = 2.2,
        dimensions: list | tuple = [0, 0, 0],
        mass: float = 0.0,
        com_offset: np.ndarray = None,
        omega_earth: float = CONSTANTS["omega_E"],
        r_earth: float = CONSTANTS["R"],
        f_earth: float = 1.0 / 298.257223563,
    ):
        self.Cd = Cd
        self.dx, self.dy, self.dz = dimensions
        self.mass = mass
        self.com_offset = (
            np.array(com_offset, dtype=float)
            if com_offset is not None
            else np.zeros(3)
        )
        print(f"PYMSIS active: {HAS_PYMSIS}")

        self.omega_e_vec = np.array([0.0, 0.0, omega_earth])
        self.r_earth = r_earth
        self.f_earth = f_earth

        # Pola ścian prostopadłościanu [m^2]
        self.area_x = self.dy * self.dz
        self.area_y = self.dx * self.dz
        self.area_z = self.dx * self.dy

    def _eci_to_geodetic(
        self, r_eci: np.ndarray
    ) -> tuple[float, float, float]:
        """Przekształca pozycję ECI [m] do geodezyjnej szerokości, długości
        i wysokości nad elipsoidą WGS-84 [m].
        """
        x, y, z = r_eci
        lon = np.degrees(np.arctan2(y, x))

        e2 = 2 * self.f_earth - self.f_earth**2
        p = np.sqrt(x**2 + y**2)

        lat = np.arctan2(z, p * (1 - e2))
        for _ in range(5):
            N = self.r_earth / np.sqrt(1 - e2 * np.sin(lat) ** 2)
            h = p / np.cos(lat) - N
            lat = np.arctan2(z, p * (1 - e2 * (N / (N + h))))

        N = self.r_earth / np.sqrt(1 - e2 * np.sin(lat) ** 2)
        alt = p / np.cos(lat) - N
        return np.degrees(lat), lon, alt

    def get_density(
        self,
        r_eci: np.ndarray,
        dt: datetime = None,
        f107: float = 150.0,
        f107a: float = 150.0,
        ap: float = 4.0,
    ) -> float:
        """Oblicza gęstość atmosfery rho [kg/m^3]."""
        lat, lon, alt_m = self._eci_to_geodetic(r_eci)

        if alt_m < 0.0:
            alt_m = 0.0

        if HAS_PYMSIS:
            if dt is None:
                dt = datetime.now(timezone.utc)

            dt_naive = dt.replace(tzinfo=None)

            output = msis.run(
                [dt_naive],
                [lon],
                [lat],
                [alt_m / 1000.0],
                f107s=[f107],
                f107as=[f107a],
                aps=[ap],
                version="0",
            )
            
            return float(output[..., Variable.MASS_DENSITY].squeeze())
        else:
            rho_0 = 1.225  # kg/m^3
            h_scale = 8500.0  # m
            return rho_0 * np.exp(-alt_m / h_scale)

    def _compute_area_and_cop(
        self, u_v_body: np.ndarray
    ) -> tuple[float, np.ndarray]:
        """Oblicza efektywną powierzchnię rzutowaną A oraz środek naporu (CoP)
        w układzie Body dla przepływu skierowanego wzdłuż u_v_body.
        """
        ux, uy, uz = np.abs(u_v_body)

        A_proj = ux * self.area_x + uy * self.area_y + uz * self.area_z

        if A_proj == 0:
            return 0.0, np.zeros(3)

        cop_x = np.sign(u_v_body[0]) * (self.dx / 2.0) if ux > 0 else 0.0
        cop_y = np.sign(u_v_body[1]) * (self.dy / 2.0) if uy > 0 else 0.0
        cop_z = np.sign(u_v_body[2]) * (self.dz / 2.0) if uz > 0 else 0.0

        cop = (
            ux * self.area_x * np.array([cop_x, 0.0, 0.0])
            + uy * self.area_y * np.array([0.0, cop_y, 0.0])
            + uz * self.area_z * np.array([0.0, 0.0, cop_z])
        ) / A_proj

        return A_proj, cop

    def compute_disturbance(
        self,
        r_eci: np.ndarray,
        v_eci: np.ndarray,
        q_body: np.ndarray,
        dt: datetime = None,
        f107: float = 150.0,
        f107a: float = 150.0,
        ap: float = 4.0,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Oblicza siłę oporu w ECI [N] oraz moment obrotowy w Body Frame [Nm].

        :return: (f_drag_eci, tau_drag_body)
        """
        # 1. Prędkość względna atmosfery z uwzględnieniem rotacji Ziemi
        v_rel_eci = v_eci - np.cross(self.omega_e_vec, r_eci)
        v_rel_norm = np.linalg.norm(v_rel_eci)

        if v_rel_norm == 0:
            return np.zeros(3), np.zeros(3)

        u_v_eci = v_rel_eci / v_rel_norm

        # 2. Poprawna macierz obrotu R_eci_to_body z kwaternionu q = [q0, q1, q2, q3]
        q0, q1, q2, q3 = q_body
        R_eci_to_body = quaternion_to_rotation_matrix(q_body).T

        u_v_body = R_eci_to_body @ u_v_eci

        # 3. Gęstość atmosfery oraz powierzchnia i CoP
        rho = self.get_density(r_eci, dt=dt, f107=f107, f107a=f107a, ap=ap)
        A_proj, r_cop = self._compute_area_and_cop(u_v_body)

        # 4. Wartość siły oporu [N]
        f_drag_mag = 0.5 * rho * (v_rel_norm**2) * self.Cd * A_proj

        # Wektor siły w ECI
        f_drag_eci = -f_drag_mag * u_v_eci

        # Wektor siły w Body Frame
        f_drag_body = -f_drag_mag * u_v_body

        # Wektor ramienia siły względem środka masy (CoM)
        r_arm = r_cop - self.com_offset

        # Moment obrotowy w Body Frame: tau = r x F
        tau_drag_body = np.cross(r_arm, f_drag_body)


        return f_drag_eci, tau_drag_body