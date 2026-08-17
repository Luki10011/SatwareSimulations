from dataclasses import dataclass
import numpy as np

@dataclass
class SatelliteState:
    p: np.ndarray  # [x, y, z] w [m]
    v: np.ndarray  # [vx, vy, vz] w [m/s]
    q: np.ndarray  # [qw, qx, qy, qz] (quaternion orientation)
    omega: np.ndarray  # [wx, wy, wz] w [rad/s]

    def to_vector(self) -> np.ndarray:
        return np.hstack([self.p, self.v, self.q, self.omega])

    @classmethod
    def from_vector(cls, y: np.ndarray) -> "SatelliteState":
        p = y[0:3]
        v = y[3:6]
        q = y[6:10]
        q = q / np.linalg.norm(q)
        omega = y[10:13]
        return cls(p=p, v=v, q=q, omega=omega)