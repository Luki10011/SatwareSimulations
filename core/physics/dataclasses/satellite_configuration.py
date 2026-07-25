from dataclasses import dataclass
import numpy as np

@dataclass
class SatelliteMechanicalConfiguration:
    m : float                   # mass of the satellite [kg]
    I : np.ndarray              # inertia tensor [kg * m^2]
    a : float                   # length of edge [m]

@dataclass 
class SatelliteCoilsConfiguration:
    N : int             # number of windings [-]
    A : float           # area of [m^2]
    I_max : float       # maximal current [A]  


@dataclass
class SatelliteReactionWheelsConfiguration:
    

