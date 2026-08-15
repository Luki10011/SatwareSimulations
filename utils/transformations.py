import math
from typing import Tuple
import numpy as np


def euler_to_quaternion(roll: float, pitch: float, yaw: float, degrees: bool = True) -> np.ndarray:
    """
    Konwertuje kąty Eulera (sekwencja ZYX / 3-2-1: Roll, Pitch, Yaw) na znormalizowany kwaternion [w, x, y, z].
    
    :param roll: Przechylenie (ϕ, obrót wokół osi X)
    :param pitch: Pochylenie (θ, obrót wokół osi Y)
    :param yaw: Odchylenie (ψ, obrót wokół osi Z)
    :param degrees: Flaga określająca, czy kąty wejściowe są w stopniach (domyślnie True)
    :return: Kwaternion [w, x, y, z]
    """
    if degrees:
        roll = math.radians(roll)
        pitch = math.radians(pitch)
        yaw = math.radians(yaw)

    # Połowy kątów
    cr = math.cos(roll * 0.5)
    sr = math.sin(roll * 0.5)
    cp = math.cos(pitch * 0.5)
    sp = math.sin(pitch * 0.5)
    cy = math.cos(yaw * 0.5)
    sy = math.sin(yaw * 0.5)

    # Wzory dla sekwencji ZYX
    w = cr * cp * cy + sr * sp * sy
    x = sr * cp * cy - cr * sp * sy
    y = cr * sp * cy + sr * cp * sy
    z = cr * cp * sy - sr * sp * cy

    q = np.array([w, x, y, z], dtype=np.float64)
    return q / np.linalg.norm(q)


def quaternion_to_euler(q: np.ndarray, degrees: bool = True) -> Tuple[float, float, float]:
    """
    Konwertuje kwaternion [w, x, y, z] na kąty Eulera (sekwencja ZYX / 3-2-1: Roll, Pitch, Yaw).
    
    :param q: Kwaternion w postaci [w, x, y, z]
    :param degrees: Flaga określająca, czy zwracać wyniki w stopniach (domyślnie True)
    :return: Krotka (roll, pitch, yaw)
    """
    # Normalizacja dla stabilności numerycznej
    q = q / np.linalg.norm(q)
    w, x, y, z = q[0], q[1], q[2], q[3]

    # Roll (X-axis)
    sinr_cosp = 2.0 * (w * x + y * z)
    cosr_cosp = 1.0 - 2.0 * (x * x + y * y)
    roll = math.atan2(sinr_cosp, cosr_cosp)

    # Pitch (Y-axis) z zabezpieczeniem przed Gimbal Lock (clamp do range [-1, 1])
    sinp = 2.0 * (w * y - z * x)
    sinp = max(-1.0, min(1.0, sinp))
    pitch = math.asin(sinp)

    # Yaw (Z-axis)
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    yaw = math.atan2(siny_cosp, cosy_cosp)

    if degrees:
        return math.degrees(roll), math.degrees(pitch), math.degrees(yaw)
    
    return roll, pitch, yaw