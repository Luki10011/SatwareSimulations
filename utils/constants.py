from typing import Dict, Any

import numpy as np

CONSTANTS : Dict[str, float] ={
    "M" : 5.97219e24,                         # Mass of Earth in kg
    "g" : np.array([0, 0, 9.81]).T,           # Acceleration due to gravity in m/s^2 (vector)
    "G" : 6.67430e-11,                        # Gravitational constant in m^3 kg^-1 s^-2
    "mu" : 3.986004418e14,                    # Standard gravitational parameter for Earth in m^3 s^-2
    "J2" : 1.08263e-3,                        # Second zonal harmonic coefficient for Earth
    "R" : 6.378e6,                            # Earth's radius [m]
    "pi" : 3.14159                            # pi constant
}

ISS : Dict[str, float] = {
    "semi_major_axis" : 6.731e3,                # Semi-major axis of the ISS orbit in kilometers
    "eccentricity" : 0.0,                       # Eccentricity of the ISS orbit
    "inclination" : 51.64,                      # Inclination of the ISS orbit
    "raan" : 0.0,                               # Right Ascension of the Ascending Node (RAAN) of the ISS orbit in degrees
    "arg_perigee" : 0.0,                        # Argument of perigee of the ISS orbit in degrees
    "true_anomaly" : 0.0                        # True anomaly of the ISS orbit in degrees
}

MOLNIYA : Dict[str, float] = {
    "semi_major_axis" : 26.6e3,                 # Semi-major axis of the Molniya orbit in kilometers
    "eccentricity" : 0.74,                      # Eccentricity of the Molniya orbit
    "inclination" : 63.43494,                       # Inclination of the Molniya orbit
    "raan" : 0.0,                               # Right Ascension of the Ascending Node (RAAN) of the Molniya orbit in degrees
    "arg_perigee" : 270.0,                      # Argument of perigee of the Molniya orbit in degrees
    "true_anomaly" : 0.0                        # True anomaly of the Molniya orbit in degrees
}

GEO : Dict[str, float] = {
    "semi_major_axis" : 42.164e3,                # Semi-major axis of the Geostationary orbit in kilometers
    "eccentricity" : 0.0,                        # Eccentricity of the Geostationary orbit
    "inclination" : 0.0,                         # Inclination of the Geostationary orbit
    "raan" : 0.0,                                # Right Ascension of the Ascending Node (RAAN) of the Geostationary orbit in degrees
    "arg_perigee" : 0.0,                         # Argument of perigee of the Geostationary orbit in degrees
    "true_anomaly" : 0.0                         # True anomaly of the Geostationary orbit in degrees
}

SUN_SYNCHRONOUS : Dict[str, float] = {
    "semi_major_axis" : 7.12e3,                   # Semi-major axis
    "eccentricity" : 0.00,                        # Eccentricity
    "inclination" : 98.0,                         # Inclination
    "raan" : 0.0,                                 # Right Ascension of the Ascending Node (RAAN) in degrees
    "arg_perigee" : 0.0,                          # Argument of perigee in degrees
    "true_anomaly" : 0.0                          # True anomaly in degrees
}

ORBITS_DATA: Dict[str, Dict[str, Any]] = {
    "ISS (International Space Station)": {
        "elements": ISS,
        "description": (
            "<b>International Space Station (ISS)</b><br><br>"
            "A classic example of a circular Low Earth Orbit (LEO). The spacecraft operates at an "
            "altitude of approximately 400 km above the Earth's surface.<br><br>"
            "<b>Technical Characteristics:</b><br>"
            "• <b>Orbital Period:</b> ~93 minutes.<br>"
            "• <b>Inclination (51.64°):</b> Intentionally selected to allow the ground track to pass over "
            "the majority of the world's populated areas and to enable launch windows from both American (Cape Canaveral) "
            "and Russian (Baikonur) cosmodromes.<br>"
            "• Due to trace atmospheric drag at this altitude, the orbit requires periodic reboosts using onboard thrusters."
        )
    },
    "Geostationary Orbit (GEO)": {
        "elements": GEO,
        "description": (
            "<b>Geostationary Orbit (GEO)</b><br><br>"
            "A special case of a geosynchronous orbit with zero inclination (i = 0°) and zero eccentricity (e = 0), "
            "lying directly above the Earth's equator.<br><br>"
            "<b>Technical Characteristics:</b><br>"
            "• <b>Radius (42,164 km):</b> Corresponds to an altitude of exactly 35,786 km above sea level.<br>"
            "• <b>Orbital Period:</b> Matches Earth's sidereal rotation period exactly (23h 56m 04s).<br>"
            "• <b>Application:</b> A satellite in this orbit remains stationary relative to a fixed point on the Earth's surface. "
            "This is critical for global telecommunications, satellite television, and continuous meteorological observation."
        )
    },
    "Molniya Orbit (HEO)": {
        "elements": MOLNIYA,
        "description": (
            "<b>Molniya Orbit (HEO)</b><br><br>"
            "A highly eccentric orbit (HEO) with an orbital period of approximately 12 hours, originally designed by the USSR "
            "to provide communications over high-latitude and polar regions where GEO satellites have poor visibility.<br><br>"
            "<b>Technical Characteristics:</b><br>"
            "• <b>Critical Inclination (63.4°):</b> The specific angle where the perturbation caused by Earth's oblateness "
            "(the J2 coefficient) results in zero rotation of the argument of perigee, stabilizing the apogee position in space.<br>"
            "• <b>Argument of Perigee (270°):</b> Ensures that the apogee remains constantly locked over the Northern Hemisphere.<br>"
            "• According to Kepler's Second Law, the satellite moves slowest near its apogee, spending nearly 11 out of 12 hours "
            "visible from northern ground stations."
        )
    },
    "Sun-Synchronous Orbit (SSO)": {
        "elements": SUN_SYNCHRONOUS,
        "description": (
            "<b>Sun-Synchronous Orbit (SSO)</b><br><br>"
            "A nearly polar, retrograde orbit in which the natural precession of the orbital plane caused by Earth's "
            "oblateness (J2 effect) is perfectly synchronized with the Earth's mean motion around the Sun.<br><br>"
            "<b>Technical Characteristics:</b><br>"
            "• <b>Nodal Precession:</b> The orbital plane rotates at exactly 0.9856° per day (360° per year).<br>"
            "• <b>Application:</b> The satellite passes over any given point on the Earth's surface at the same local solar time. "
            "This provides consistent sun illumination angles across different passes, which is fundamental for remote sensing, Earth observation, "
            "and imaging satellites (e.g., Landsat, Sentinel missions) to simplify change detection analysis."
        )
    }
}