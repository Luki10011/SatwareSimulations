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


def quaternion_to_euler(
    q: np.ndarray, degrees: bool = True
) -> Tuple[float, float, float]:
    """Konwertuje kwaternion [w, x, y, z] na kąty Eulera (sekwencja ZYX / 3-2-1: Roll, Pitch, Yaw).

    Zawiera odporność na osobliwość Gimbal Lock (Pitch = +-90 deg).

    :param q: Kwaternion w postaci [w, x, y, z]
    :param degrees: Flaga określająca, czy zwracać wyniki w stopniach
        (domyślnie True)
    :return: Krotka (roll, pitch, yaw)
    """
    # Normalizacja dla stabilności numerycznej
    norm = np.linalg.norm(q)
    if norm < 1e-12:
        return (0.0, 0.0, 0.0)

    q = q / norm
    w, x, y, z = q[0], q[1], q[2], q[3]

    # Test obecności osobliwości Gimbal Lock (Gimbal Lock detection)
    # sinp = 2.0 * (w * y - z * x)
    sinp = 2.0 * (w * y - z * x)

    # Próg tolerancji numerycznej blisko +-1.0 (np. 0.999999)
    if abs(sinp) >= 0.999999:
        # Pitch osiaga dokładnie +90 lub -90 stopni
        pitch = math.copysign(math.pi / 2.0, sinp)

        # W osobliwości osie Roll i Yaw nakładają się na siebie.
        # Przypisujemy cały obrót do Roll, a Yaw wyzerowujemy dla ciągłości.
        roll = 2.0 * math.atan2(x, w)
        yaw = 0.0
    else:
        # Standardowy przypadek (poza osobliwością Gimbal Lock)
        sinr_cosp = 2.0 * (w * x + y * z)
        cosr_cosp = 1.0 - 2.0 * (x * x + y * y)
        roll = math.atan2(sinr_cosp, cosr_cosp)

        pitch = math.asin(max(-1.0, min(1.0, sinp)))

        siny_cosp = 2.0 * (w * z + x * y)
        cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
        yaw = math.atan2(siny_cosp, cosy_cosp)

    if degrees:
        return math.degrees(roll), math.degrees(pitch), math.degrees(yaw)

    return roll, pitch, yaw