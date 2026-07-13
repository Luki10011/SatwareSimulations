
from utils.constants import  CONSTANTS
from core.physics.orbits import Orbit
import numpy as np

class J2Perturbator:

    def __init__(self, orbit : Orbit):

        self.orbit = orbit
        self.R_Z = CONSTANTS["R"]
        self.J2 = CONSTANTS["J2"]
        self.mu = CONSTANTS["mu"] 
        self.a = self.orbit.orbitalElements.semi_major_axis
        self.e = self.orbit.orbitalElements.eccentricity
        self.i = self.orbit.orbitalElements.inclination
        self.n = np.sqrt(self.mu / self.a ** 3)
        self.p = self.a * (1 - self.e ** 2)
        self._caluclate_orbital_changes()

    def _caluclate_orbital_changes(self):
        mul_factor = (3 * self.n * self.J2 * self.R_Z ** 2) / (2 * self.p ** 2)
        
        EPSILON = 1e-6          
        SNAP_THRESHOLD = 1e-10  
        
        is_equatorial = (self.i < EPSILON) or np.isclose(self.i, np.pi, atol=EPSILON)
        
        if is_equatorial:
            self.mean_nodal_regression = 0.0
            self.mean_apsidal_precession = mul_factor
        else:
            self.mean_nodal_regression = -mul_factor * np.cos(self.i)
            self.mean_apsidal_precession = (mul_factor / 2) * (4 - 5 * np.sin(self.i) ** 2)
        
        if self.e < EPSILON:
            self.mean_apsidal_precession = 0.0

        if abs(self.mean_nodal_regression) < SNAP_THRESHOLD:
            self.mean_nodal_regression = 0.0
            
        if abs(self.mean_apsidal_precession) < SNAP_THRESHOLD:
            self.mean_apsidal_precession = 0.0
        

        
