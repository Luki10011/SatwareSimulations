import numpy as np
import datetime

def rotate_pqw_to_eci(vector_pqw: np.ndarray, raan: float, inclination: float, arg_perigee: float) -> np.ndarray:
    """
    Transformuje wektor z układu peryfokalnego (PQW) do układu inercjalnego (ECI).
    
    :param vector_pqw: wektor 3D [x, y, z] w układzie PQW
    :param raan: długość węzła wstępującego (Ω) w radianach
    :param inclination: inklinacja (i) w radianach
    :param arg_perigee: argument perycentrum (ω) w radianach
    :return: wektor 3D w układzie ECI
    """
    
    # Obliczanie elementów macierzy rotacji
    cos_raan, sin_raan = np.cos(raan), np.sin(raan)
    cos_i, sin_i = np.cos(inclination), np.sin(inclination)
    cos_w, sin_w = np.cos(arg_perigee), np.sin(arg_perigee)
    
    # Macierz rotacji R = Rz(-raan) * Rx(-i) * Rz(-w)
    # Jest to standardowa macierz transformacji dla problemu dwóch ciał
    R = np.array([
        [
            cos_raan * cos_w - sin_raan * cos_i * sin_w,
            -cos_raan * sin_w - sin_raan * cos_i * cos_w,
            sin_raan * sin_i
        ],
        [
            sin_raan * cos_w + cos_raan * cos_i * sin_w,
            -sin_raan * sin_w + cos_raan * cos_i * cos_w,
            -cos_raan * sin_i
        ],
        [
            sin_i * sin_w,
            sin_i * cos_w,
            cos_i
        ]
    ])
    
    return R @ vector_pqw

def get_pqw_to_eci_matrix(raan: float, inclination: float, arg_perigee: float) -> np.ndarray:
    cos_raan, sin_raan = np.cos(raan), np.sin(raan)
    cos_i, sin_i = np.cos(inclination), np.sin(inclination)
    cos_w, sin_w = np.cos(arg_perigee), np.sin(arg_perigee)
    
    R = np.array([
        [
            cos_raan * cos_w - sin_raan * cos_i * sin_w,
            -cos_raan * sin_w - sin_raan * cos_i * cos_w,
            sin_raan * sin_i
        ],
        [
            sin_raan * cos_w + cos_raan * cos_i * sin_w,
            -sin_raan * sin_w + cos_raan * cos_i * cos_w,
            -cos_raan * sin_i
        ],
        [
            sin_i * sin_w,
            sin_i * cos_w,
            cos_i
        ]
    ])
    
    return R

def datetime_to_julian_date(dt: datetime.datetime) -> float:
    """
    Konwertuje obiekt datetime (wymagany UTC) na Dni Juliańskie (Julian Date).
    """
    # Upewniamy się, że obiekt datetime ma przypisaną strefę UTC
    if dt.tzinfo is None:
        # Jeśli obiekt nie ma strefy, bezpiecznie zakładamy, że to UTC
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    else:
        dt = dt.astimezone(datetime.timezone.utc)

    year = dt.year
    month = dt.month
    day = dt.day

    # Dostosowanie algorytmu dla stycznia i lutego
    if month <= 2:
        year -= 1
        month += 12

    # Uwzględnienie poprawki kalendarza gregoriańskiego
    A = int(year / 100)
    B = 2 - A + int(A / 4)

    # Obliczenie pełnych dni juliańskich (w południe)
    jd_whole = int(365.25 * (year + 4716)) + int(30.6001 * (month + 1)) + day + B - 1524.5

    # Dodanie ułamka dnia (godziny, minuty, sekundy, mikrosekundy)
    day_fraction = (dt.hour + dt.minute / 60.0 + dt.second / 3600.0 + dt.microsecond / 3600000000.0) / 24.0

    return jd_whole + day_fraction

def get_initial_gmst(julian_date: float) -> float:
    """
    Zwraca kąt w stopniach między osią X ECI a osią X ECEF dla danej daty juliańskiej.
    """
    d = julian_date - 2451545.0  # Dni od epoki J2000.0 (1 stycznia 2000, 12:00 UTC)
    gmst = 280.46061837 + 360.98564736629 * d
    return gmst % 360.0