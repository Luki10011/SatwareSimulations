import matplotlib.pyplot as plt
import numpy as np
from core.physics.dataclasses.orbital_data import OrbitalElements
from core.physics.orbits import Orbit   
from utils.plotting.orbit_plotter import plot_orbit

def run_test():
    elements = OrbitalElements(
        semi_major_axis=26.6e6, 
        eccentricity=0.72,       
        inclination=np.radians(63.4), # 45 stopni
        raan=np.radians(0),
        arg_perigee=np.radians(270),
        true_anomaly=0.0
    )
    
    orbit = Orbit(elements)
    
    orbit.create_simple_orbit()

    plot_orbit(orbit)
    
    

if __name__ == "__main__":
    run_test()