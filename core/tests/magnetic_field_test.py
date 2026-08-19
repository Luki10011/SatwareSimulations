


from typing import List

from core.physics.dataclasses.orbital_data import OrbitalElements, OrbitalStateVector
from core.physics.orbits import Orbit
from core.physics.sensors.magnetometer import Magnetometer
from utils.constants import CONSTANTS
import numpy as np

import numpy as np
import matplotlib.pyplot as plt
import ppigrf
from datetime import datetime


def magnetic_field_test():
    orbital_elements: OrbitalElements = OrbitalElements(
        semi_major_axis=CONSTANTS["R"] + 600e3,
        eccentricity=0,
        raan=0,
        true_anomaly=0,
        inclination=np.radians(56),
        arg_perigee=0
    )

    orbit = Orbit(orbitalElements=orbital_elements)

    states: List[OrbitalStateVector] = orbit.generate_orbit_by_time()

    magnetometer = Magnetometer()

    date = "2026-08-19"

    magnetic_field_eci = []

    for state in states:
        b_eci = magnetometer.get_magnetic_field_in_eci_frame(
            date=date,
            pos_m=state.p
        )

        magnetic_field_eci.append(b_eci)

    magnetic_field_eci = np.asarray(magnetic_field_eci)

    # ==========================================================
    # Wyniki
    # ==========================================================

    print("\n===== MAGNETIC FIELD ECI =====")

    print(f"Liczba punktów: {len(magnetic_field_eci)}")

    print("\nPierwszy punkt:")
    print(f"Bx = {magnetic_field_eci[0, 0] * 1e6:.3f} µT")
    print(f"By = {magnetic_field_eci[0, 1] * 1e6:.3f} µT")
    print(f"Bz = {magnetic_field_eci[0, 2] * 1e6:.3f} µT")

    print("\nOstatni punkt:")
    print(f"Bx = {magnetic_field_eci[-1, 0] * 1e6:.3f} µT")
    print(f"By = {magnetic_field_eci[-1, 1] * 1e6:.3f} µT")
    print(f"Bz = {magnetic_field_eci[-1, 2] * 1e6:.3f} µT")

    print("\nZakresy:")

    print(
        f"Bx: "
        f"{magnetic_field_eci[:, 0].min() * 1e6:.3f} "
        f"-> "
        f"{magnetic_field_eci[:, 0].max() * 1e6:.3f} µT"
    )

    print(
        f"By: "
        f"{magnetic_field_eci[:, 1].min() * 1e6:.3f} "
        f"-> "
        f"{magnetic_field_eci[:, 1].max() * 1e6:.3f} µT"
    )

    print(
        f"Bz: "
        f"{magnetic_field_eci[:, 2].min() * 1e6:.3f} "
        f"-> "
        f"{magnetic_field_eci[:, 2].max() * 1e6:.3f} µT"
    )

    # ==========================================================
    # Moduł pola
    # ==========================================================

    magnetic_field_magnitude = np.linalg.norm(
        magnetic_field_eci,
        axis=1
    )

    print("\nModuł pola:")

    print(
        f"|B|: "
        f"{magnetic_field_magnitude.min() * 1e6:.3f} "
        f"-> "
        f"{magnetic_field_magnitude.max() * 1e6:.3f} µT"
    )

    # ==========================================================
    # Wykres
    # ==========================================================

    time = np.arange(len(magnetic_field_eci))

    plt.figure(figsize=(10, 6))

    plt.plot(
        time,
        magnetic_field_eci[:, 0] * 1e6,
        label="X"
    )

    plt.plot(
        time,
        magnetic_field_eci[:, 1] * 1e6,
        label="Y"
    )

    plt.plot(
        time,
        magnetic_field_eci[:, 2] * 1e6,
        label="Z"
    )

    plt.xlabel("Time [s]")
    plt.ylabel("Magnetic Field [µT]")
    plt.title("Magnetic Field in ECI")
    plt.grid()
    plt.legend()

    plt.show()

    return magnetic_field_eci

if __name__ == "__main__":
    magnetic_field_test()
