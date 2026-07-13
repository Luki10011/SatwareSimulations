
from core.physics.orbits import Orbit
import numpy as np
import matplotlib.pyplot as plt

def plot_orbit(orbit: Orbit):
    """
    Plots the trajectory along with geometric indicators of orbital elements.
    """
    elements = orbit.orbitalElements
    positions = np.array([state.p for state in orbit.orbitalState])
    
    fig = plt.figure(figsize=(12, 9))
    ax = fig.add_subplot(111, projection='3d')
    
    # 1. Plot trajectory and Earth
    ax.plot(positions[:, 0], positions[:, 1], positions[:, 2], label='Trajectory', color='orange')
    ax.scatter(0, 0, 0, color='blue', s=100, label='Earth')
    
    # 2. Add visual markers for orbital elements
    # Periapsis (perycentrum) - point at nu=0

    if elements.eccentricity != 0:
        periapsis = min(positions, key=lambda p: np.linalg.norm(p))
        ax.scatter(periapsis[0], periapsis[1], periapsis[2], color='red', s=50, label='Periapsis')
        
        # Line of Apsides (linie apsyd) - line from focus through periapsis to apoapsis
        # Apoapsis is approx at the opposite side of the orbit
        apoapsis = max(positions, key=lambda p: np.linalg.norm(p))
        ax.scatter(apoapsis[0], apoapsis[1], apoapsis[2], color='red', s=50, label='Apoapsis')

        ax.plot([periapsis[0], apoapsis[0]], [periapsis[1], apoapsis[1]], [periapsis[2], apoapsis[2]], 
                'r--', alpha=0.5, label='Line of Apsides')
        
    # 3. Add ECI basis vectors
    vec_len = 1.2 * elements.semi_major_axis 
    ax.quiver(0, 0, 0, vec_len, 0, 0, color='red', alpha=0.3, label='X-axis')
    ax.quiver(0, 0, 0, 0, vec_len, 0, color='green', alpha=0.3, label='Y-axis')
    ax.quiver(0, 0, 0, 0, 0, vec_len, color='blue', alpha=0.3, label='Z-axis')

    
    # 4. Final plot adjustments
    ax.set_xlabel('X [km]')
    ax.set_ylabel('Y [km]')
    ax.set_zlabel('Z [km]')
    ax.legend()
    
    # Equal aspect ratio logic
    max_range = np.max(np.abs(positions)) * 1.1
    ax.set_xlim(-max_range, max_range)
    ax.set_ylim(-max_range, max_range)
    ax.set_zlim(-max_range, max_range)
    
    plt.show()