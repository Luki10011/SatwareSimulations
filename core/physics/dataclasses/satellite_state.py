from dataclasses import dataclass
import numpy as np

@dataclass
class SatteliteState:
    p : np.ndarray          # position of the satellite [m]
    v : np.ndarray          # velocity of the satellite [m/s]
    q : np.ndarray          # orientation quaternion    [-]
    omega : np.ndarray      # angular velocity          [rad/s]