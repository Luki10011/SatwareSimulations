import numpy as np

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