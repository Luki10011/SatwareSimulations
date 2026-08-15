
from dataclasses import dataclass

import numpy as np

from core.physics.dataclasses.orbital_data import OrbitalElements
from ui.satellite.satellite_configurator import SatelliteConfigurator
import numpy as np

TRUE_ANOMALY_MIN = -360.0
TRUE_ANOMALY_MAX = 360.0
EULER_ANGLE_MIN = -360.0
EULER_ANGLE_MAX = 360.0
ANGULAR_VELOCITY_MIN = -1000.0
ANGULAR_VELOCITY_MAX = 1000.0


@dataclass
class SimulationConfiguration:
    orbital_data: OrbitalElements
    satellite_configuration: SatelliteConfigurator
    initial_position: np.ndarray
    initial_velocities: np.ndarray
    initial_quat_orientation: np.ndarray
    initial_angular_velocities: np.ndarray

