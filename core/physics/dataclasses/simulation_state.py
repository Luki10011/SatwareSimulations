from dataclasses import dataclass

from core.physics.dataclasses.satellite_state import SatelliteState


@dataclass
class SimulationState:
    t: float = 0.0  # Czas symulacji [s]
    step_count: int = 0  # Liczba wykonanych kroków
    dt: float = 0.1  # Stały krok całki [s]
    satellite: SatelliteState = None