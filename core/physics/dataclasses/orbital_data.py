from dataclasses import dataclass
import numpy as np

@dataclass
class OrbitalElements:
    semi_major_axis: float  # semi major axis (a) [m]
    eccentricity: float     # eccentricity (e) [-]
    raan: float             # right ascension of the ascending node (Ω) [rad]
    inclination: float      # inclination (i) [rad]
    arg_perigee: float      # argument of the perigee (ω) [rad]
    true_anomaly: float     # true anomaly (ν) [rad]

@dataclass
class OrbitalStateVector:
    p : np.ndarray          # trajectory point [m]
    v : np.ndarray          # velocity [m/s]
