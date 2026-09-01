import numpy as np
from dataclasses import dataclass
from typing import Any, Dict, List

from pyparsing import Optional

# Physical validation constants for CubeSats / Microsatellites
MASS_MIN = 0.1          # kg
MASS_MAX = 50.0         # kg

DIM_MIN = 0.05          # m
DIM_MAX = 1.0           # m

INERTIA_RATIO_MIN = 0.2 # Minimum multiplier relative to a solid box J_box
INERTIA_RATIO_MAX = 3.0 # Maximum multiplier relative to a solid box J_box

COIL_TURNS_MIN = 1
COIL_TURNS_MAX = 5000

COIL_AREA_MIN = 0.0001  # m^2 (1 cm^2)
COIL_AREA_MAX = DIM_MAX**2       # m^2

MAX_CURRENT_MIN = 0.01  # A
MAX_CURRENT_MAX = 10.0  # A

MIN_REACTION_WHEEL_RPM = 3000.0
MAX_REACTION_WHEEL_RPM = 10000.0


@dataclass
class SatelliteMechanicalConfiguration:
    m: float                   # mass of the satellite [kg]
    I: np.ndarray              # inertia tensor [kg * m^2]
    a: float                   # length of edge [m]
    b: float                   # width of edge [m]
    h: float                   # height of edge [m]


@dataclass
class SatelliteCoilsConfiguration:
    N: int                     # number of windings [-]
    A: float                   # area [m^2]
    I_max: float               # maximal current [A]


@dataclass
class SatelliteReactionWheelsConfiguration:
    configuration: str        # "principal" or "pyramid"
    wheel_count: int          # number of wheels
    wheel_mass: float         # wheel mass [kg]
    wheel_radius: float       # wheel radius [m]
    wheel_height: float       # wheel thickness / height [m]
    wheel_max_speed: float    # max angular speed [rpm]
    inertia_tensor: np.ndarray  # inertia tensor of the reaction wheel assembly [kg * m^2]


@dataclass
class SatelliteConfiguration:
    mechanical: SatelliteMechanicalConfiguration
    electromagnetic: SatelliteCoilsConfiguration
    reaction_wheels: SatelliteReactionWheelsConfiguration


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def calculate_box_inertia_tensor(mass: float, a: float, b: float, h: float) -> np.ndarray:
    """Calculate theoretical diagonal inertia tensor for a solid box of mass m and dimensions (a, b, h)."""
    j_xx = (1.0 / 12.0) * mass * (b**2 + h**2)
    j_yy = (1.0 / 12.0) * mass * (a**2 + h**2)
    j_zz = (1.0 / 12.0) * mass * (a**2 + b**2)
    return np.diag([j_xx, j_yy, j_zz])


def skew_symmetric_matrix(vector: np.ndarray) -> np.ndarray:
    """Return the 3x3 skew-symmetric matrix S(r) for a 3D vector."""
    x, y, z = vector
    return np.array(
        [
            [0.0, -z, y],
            [z, 0.0, -x],
            [-y, x, 0.0]
        ],
        dtype=float
    )


def calculate_rotation_matrix_to_axis(target_axis: np.ndarray) -> np.ndarray:
    """
    Computes rotation matrix T_Ri that aligns local z-axis [0, 0, 1] with target_axis n_Ri.
    Uses Rodrigues' rotation formula.
    """
    z_local = np.array([0.0, 0.0, 1.0], dtype=float)
    n_ri = np.array(target_axis, dtype=float)
    
    norm = np.linalg.norm(n_ri)
    if norm == 0.0:
        return np.eye(3, dtype=float)
    n_ri = n_ri / norm

    dot_prod = np.dot(z_local, n_ri)

    if np.isclose(dot_prod, 1.0):
        return np.eye(3, dtype=float)
    
    if np.isclose(dot_prod, -1.0):
        return np.diag([1.0, -1.0, -1.0])

    v = np.cross(z_local, n_ri)
    s_v = skew_symmetric_matrix(v)
    
    r_matrix = np.eye(3, dtype=float) + s_v + (s_v @ s_v) * (1.0 / (1.0 + dot_prod))
    return r_matrix


def calculate_reaction_wheel_local_inertia(wheel_mass: float, wheel_radius: float, wheel_height: float) -> np.ndarray:
    """
    Return local inertia tensor I_RWi for a cylindrical wheel in its own frame (spin axis along z_local).
    """
    if wheel_mass <= 0.0 or wheel_radius <= 0.0 or wheel_height <= 0.0:
        return np.zeros((3, 3), dtype=float)

    j_spin = 0.5 * wheel_mass * (wheel_radius**2)  # Os obrotu (z_local)
    j_transverse = (1.0 / 12.0) * wheel_mass * (3.0 * (wheel_radius**2) + (wheel_height**2))

    return np.diag([j_transverse, j_transverse, j_spin])


def calculate_axisymmetric_cylinder_inertia_tensor(
    wheel_mass: float = None,
    wheel_radius: float = None,
    wheel_height: float = None,
    axis: np.ndarray = None,
    wheel_tensor : np.ndarray = None
) -> np.ndarray:
    """
    Transform wheel inertia tensor from local frame to body frame: I_Ri^B = T_Ri^T * I_RWi * T_Ri
    (Eq. tensor_transformacja)
    """
    if wheel_tensor is not None:
        i_rwi = np.asarray(wheel_tensor, dtype=float)
        if i_rwi.shape != (3, 3):
            raise ValueError()
    else:
        if wheel_mass is None or wheel_radius is None or wheel_height is None:
            raise ValueError()
        i_rwi = calculate_reaction_wheel_local_inertia(wheel_mass, wheel_radius, wheel_height)

    if axis is None:
        axis = np.array([0.0, 0.0, 1.0], dtype=float)

    t_ri = calculate_rotation_matrix_to_axis(axis)
    i_ri_b = t_ri @ i_rwi @ t_ri.T
    
    return i_ri_b


def reaction_wheel_axes(configuration: str, wheel_count: int) -> List[np.ndarray]:
    """Return normalized spin axes n_Ri for a given reaction wheel layout."""
    config = str(configuration or "").strip().lower()
    
    if config == "pyramid" and wheel_count == 4:
        axes = [
            np.array([1.0, 1.0, 1.0], dtype=float),
            np.array([1.0, -1.0, -1.0], dtype=float),
            np.array([-1.0, 1.0, -1.0], dtype=float),
            np.array([-1.0, -1.0, 1.0], dtype=float),
        ]
    else:
        axes = [
            np.array([1.0, 0.0, 0.0], dtype=float),
            np.array([0.0, 1.0, 0.0], dtype=float),
            np.array([0.0, 0.0, 1.0], dtype=float),
        ]

    normalized_axes = []
    for axis in axes[: max(1, min(len(axes), wheel_count))]:
        norm = np.linalg.norm(axis)
        if norm > 0.0:
            normalized_axes.append(axis / norm)
            
    return normalized_axes


def calculate_total_inertia_tensor(
    mechanical_tensor: np.ndarray,
    wheel_mass: float,
    wheel_radius: float,
    wheel_height: float,
    wheel_axes: List[np.ndarray],
    wheel_offsets: List[np.ndarray] = None,
) -> np.ndarray:
    """
    Calculate full inertia tensor I_S = I_B + sum(I_RBi^B).
    Integrates coordinate rotation and Steiner's theorem.
    """
    i_s = np.array(mechanical_tensor, dtype=float, copy=True)

    for i, axis in enumerate(wheel_axes):
        i_ri_b = calculate_axisymmetric_cylinder_inertia_tensor(
            wheel_mass, wheel_radius, wheel_height, axis
        )

        if wheel_offsets is not None and i < len(wheel_offsets):
            r_ri = np.array(wheel_offsets[i], dtype=float)
        else:
            norm_axis = axis / np.linalg.norm(axis) if np.linalg.norm(axis) > 0 else axis
            r_ri = norm_axis * 0.005

        s_r = skew_symmetric_matrix(r_ri)
        steiner_term = wheel_mass * (s_r @ s_r.T)

        i_rbi_b = i_ri_b + steiner_term
        i_s += i_rbi_b
        i_s[np.abs(i_s) < 1e-15] = 0.0  
    return i_s


def validate_satellite_configuration_data(data: Dict[str, Any]) -> Dict[str, str]:
    errors: Dict[str, str] = {}

    mechanical = data.get("mechanical", {})
    electromagnetic = data.get("electromagnetic", {})
    reaction_wheels = data.get("reaction_wheels", {})

    # --- MECHANICAL VALIDATION ---
    mass = _coerce_float(mechanical.get("mass"), 0.0)
    if not (MASS_MIN <= mass <= MASS_MAX):
        errors["mass"] = f"Mechanical mass must be between {MASS_MIN} kg and {MASS_MAX} kg."

    dimensions = mechanical.get("dimensions", [])
    valid_dims = True
    if not isinstance(dimensions, (list, tuple)) or len(dimensions) != 3:
        errors["dimensions"] = "Mechanical dimensions must contain three values [a, b, h]."
        valid_dims = False
    else:
        dim_keys = ["dim_a", "dim_b", "dim_h"]
        for idx, dim_name in enumerate(["a (length)", "b (width)", "h (height)"]):
            val = _coerce_float(dimensions[idx], 0.0)
            if not (DIM_MIN <= val <= DIM_MAX):
                errors[dim_keys[idx]] = f"Dimension {dim_name} must be between {DIM_MIN} m and {DIM_MAX} m."
                valid_dims = False

    # Inertia tensor validation
    inertia_matrix = mechanical.get("inertia_tensor", [])
    if not isinstance(inertia_matrix, (list, tuple)) or len(inertia_matrix) != 3:
        errors["inertia_tensor"] = "Inertia tensor must be a 3x3 matrix."
    else:
        try:
            tensor = np.array(inertia_matrix, dtype=float)
            if tensor.shape != (3, 3):
                errors["inertia_tensor"] = "Inertia tensor must have shape (3, 3)."
            else:
                # 1. Symmetry check
                if not np.allclose(tensor, tensor.T, atol=1e-5):
                    errors["inertia_tensor"] = "Inertia tensor must be symmetric (J_ij = J_ji)."

                # 2. Check triangle inequality for principal moments
                j_xx, j_yy, j_zz = tensor[0, 0], tensor[1, 1], tensor[2, 2]
                if j_xx <= 0 or j_yy <= 0 or j_zz <= 0:
                    errors["inertia_tensor"] = "Diagonal entries of inertia tensor must be strictly positive."
                elif not (j_xx + j_yy > j_zz and j_xx + j_zz > j_yy and j_yy + j_zz > j_xx):
                    errors["inertia_tensor"] = "Inertia tensor violates physical triangle inequality (J_ii + J_jj > J_kk)."

                # 3. Compare with analytical solid box inertia multiplier bounds
                if valid_dims and MASS_MIN <= mass <= MASS_MAX:
                    a, b, h = dimensions[0], dimensions[1], dimensions[2]
                    box_tensor = calculate_box_inertia_tensor(mass, a, b, h)
                    
                    for i, axis in enumerate(["Jxx", "Jyy", "Jzz"]):
                        j_ref = box_tensor[i, i]
                        j_val = tensor[i, i]
                        min_allowed = INERTIA_RATIO_MIN * j_ref
                        max_allowed = INERTIA_RATIO_MAX * j_ref
                        if not (min_allowed <= j_val <= max_allowed):
                            errors["inertia_tensor"] = (
                                f"{axis} ({j_val:.5f}) is outside allowed range [{min_allowed:.5f}, {max_allowed:.5f}] "
                                f"relative to reference box tensor."
                            )
        except (ValueError, TypeError):
            errors["inertia_tensor"] = "Inertia tensor contains invalid numerical values."

    # --- ELECTROMAGNETIC VALIDATION ---
    coil_turns = _coerce_int(electromagnetic.get("coil_turns"), 0)
    if not (COIL_TURNS_MIN <= coil_turns <= COIL_TURNS_MAX):
        errors["coil_turns"] = f"Coil turns must be between {COIL_TURNS_MIN} and {COIL_TURNS_MAX}."

    coil_area = _coerce_float(electromagnetic.get("coil_area"), 0.0)
    if not (COIL_AREA_MIN <= coil_area <= COIL_AREA_MAX):
        errors["coil_area"] = f"Coil area must be between {COIL_AREA_MIN} m² and {COIL_AREA_MAX} m²."
    elif valid_dims:
        a, b, h = dimensions[0], dimensions[1], dimensions[2]
        max_face_area = max(a * b, a * h, b * h)
        if coil_area > max_face_area:
            errors["coil_area"] = f"Coil area ({coil_area} m²) cannot exceed satellite maximum face area ({max_face_area:.4f} m²)."

    max_current = _coerce_float(electromagnetic.get("max_current"), 0.0)
    if not (MAX_CURRENT_MIN <= max_current <= MAX_CURRENT_MAX):
        errors["max_current"] = f"Max current must be between {MAX_CURRENT_MIN} A and {MAX_CURRENT_MAX} A."

    # --- REACTION WHEELS VALIDATION ---
    configuration = str(reaction_wheels.get("configuration", "")).strip().lower()
    if configuration not in {"principal", "pyramid"}:
        errors["wheel_configuration"] = "Reaction wheels configuration must be either 'principal' or 'pyramid'."
    else:
        expected_count = 3 if configuration == "principal" else 4
        wheel_count = _coerce_int(reaction_wheels.get("wheel_count"), 0)
        if wheel_count != expected_count:
            errors["wheel_count"] = f"Reaction wheel count must be {expected_count} for configuration '{configuration}'."

        wheel_mass = _coerce_float(reaction_wheels.get("wheel_mass"), 0.0)
        wheel_radius = _coerce_float(reaction_wheels.get("wheel_radius"), 0.0)
        wheel_height = _coerce_float(reaction_wheels.get("wheel_height"), 0.0)
        wheel_max_speed = _coerce_float(reaction_wheels.get("wheel_max_speed"), 0.0)

        if wheel_mass <= 0.0:
            errors["wheel_mass"] = "Reaction wheel mass must be greater than zero."
        if wheel_radius <= 0.0:
            errors["wheel_radius"] = "Reaction wheel radius must be greater than zero."
        if wheel_height <= 0.0:
            errors["wheel_height"] = "Reaction wheel height must be greater than zero."
        if not (MIN_REACTION_WHEEL_RPM <= wheel_max_speed <= MAX_REACTION_WHEEL_RPM):
            errors["wheel_max_speed"] = f"Reaction wheel max speed must be between {MIN_REACTION_WHEEL_RPM} and {MAX_REACTION_WHEEL_RPM} RPM."

    return errors

def build_satellite_configuration(data: Dict[str, Any]) -> SatelliteConfiguration:
    mechanical = data.get("mechanical", {})
    electromagnetic = data.get("electromagnetic", {})
    reaction_wheels = data.get("reaction_wheels", {})

    dimensions = mechanical.get("dimensions", [])
    if not isinstance(dimensions, (list, tuple)) or len(dimensions) != 3:
        dimensions = []

    inertia_matrix = mechanical.get("inertia_tensor", [[0.02, 0.0, 0.0], [0.0, 0.015, 0.0], [0.0, 0.0, 0.01]])
    inertia_array = np.array(inertia_matrix, dtype=float)

    wheel_mass = _coerce_float(reaction_wheels.get("wheel_mass"), 0.25)
    wheel_radius = _coerce_float(reaction_wheels.get("wheel_radius"), 0.05)
    wheel_height = _coerce_float(reaction_wheels.get("wheel_height"), 0.02)
    wheel_max_speed = _coerce_float(reaction_wheels.get("wheel_max_speed"), 6000.0)

    wheel_tensor = calculate_reaction_wheel_local_inertia(wheel_mass, wheel_radius, wheel_height)

    return SatelliteConfiguration(
        mechanical=SatelliteMechanicalConfiguration(
            m=_coerce_float(mechanical.get("mass"), 12.5),
            I=inertia_array,
            a=_coerce_float(dimensions[0], 0.0),
            b=_coerce_float(dimensions[1], 0.0),
            h=_coerce_float(dimensions[2], 0.0),
        ),
        electromagnetic=SatelliteCoilsConfiguration(
            N=_coerce_int(electromagnetic.get("coil_turns"), 120),
            A=_coerce_float(electromagnetic.get("coil_area"), 0.04),
            I_max=_coerce_float(electromagnetic.get("max_current"), 2.5),
        ),
        reaction_wheels=SatelliteReactionWheelsConfiguration(
            configuration=str(reaction_wheels.get("configuration", "principal")).strip().lower(),
            wheel_count=_coerce_int(reaction_wheels.get("wheel_count"), 3),
            wheel_mass=wheel_mass,
            wheel_radius=wheel_radius,
            wheel_height=wheel_height,
            wheel_max_speed=wheel_max_speed,
            inertia_tensor=wheel_tensor,
        ),
    )


def serialize_satellite_configuration(config: SatelliteConfiguration) -> Dict[str, Any]:
    return {
        "mechanical": {
            "mass": config.mechanical.m,
            "dimensions": [config.mechanical.a, config.mechanical.b, config.mechanical.h],
            "inertia_tensor": config.mechanical.I.tolist(),
        },
        "electromagnetic": {
            "coil_turns": config.electromagnetic.N,
            "coil_area": config.electromagnetic.A,
            "max_current": config.electromagnetic.I_max,
        },
        "reaction_wheels": {
            "configuration": config.reaction_wheels.configuration,
            "wheel_count": config.reaction_wheels.wheel_count,
            "wheel_mass": config.reaction_wheels.wheel_mass,
            "wheel_radius": config.reaction_wheels.wheel_radius,
            "wheel_height": config.reaction_wheels.wheel_height,
            "wheel_max_speed": config.reaction_wheels.wheel_max_speed,
            "inertia_tensor": config.reaction_wheels.inertia_tensor.tolist(),
        },
    }

def _get_field(obj: Any, key: str, alt_key: str = None, default: Any = None) -> Any:
    """Bezpiecznie pobiera wartość z obiektu lub słownika."""
    if obj is None:
        return default

    # Jeśli obiekt jest słownikiem
    if isinstance(obj, dict):
        val = obj.get(key)
        if val is None and alt_key:
            val = obj.get(alt_key)
        return val if val is not None else default

    # Jeśli obiekt jest instancją klasy / dataclass
    val = getattr(obj, key, None)
    if val is None and alt_key:
        val = getattr(obj, alt_key, None)
    return val if val is not None else default


def deserialize_satellite_configuration(data: Any) -> SatelliteConfiguration:
    """Uniwersalna funkcja konwertująca słownik lub obiekt na SatelliteConfiguration."""
    if data is None:
        data = {}

    # 1. Automatyczne odpakowanie, jeśli przekazano cały payload
    if isinstance(data, dict) and "satellite_configuration" in data:
        data = data["satellite_configuration"]
    elif hasattr(data, "satellite_configuration"):
        data = getattr(data, "satellite_configuration")

    # Jeśli to już jest prawidłowa instancja SatelliteConfiguration
    if isinstance(data, SatelliteConfiguration):
        return data

    # 2. Sekcja Mechanical
    mech_raw = _get_field(data, "mechanical", default={})

    dims = _get_field(mech_raw, "dimensions")
    if dims and isinstance(dims, (list, tuple)) and len(dims) >= 3:
        a_val, b_val, h_val = dims[0], dims[1], dims[2]
    else:
        a_val = _get_field(mech_raw, "a", default=1.0)
        b_val = _get_field(mech_raw, "b", default=1.0)
        h_val = _get_field(mech_raw, "h", default=1.0)

    m_val = _get_field(mech_raw, "m", alt_key="mass", default=1.0)
    I_val = _get_field(mech_raw, "I", alt_key="inertia_tensor", default=np.eye(3))

    mechanical = SatelliteMechanicalConfiguration(
        m=float(m_val),
        I=np.asarray(I_val, dtype=np.float64),
        a=float(a_val),
        b=float(b_val),
        h=float(h_val),
    )

    # 3. Sekcja Electromagnetic
    em_raw = _get_field(data, "electromagnetic", default={})

    N_val = _get_field(em_raw, "N", alt_key="coil_turns", default=100)
    A_val = _get_field(em_raw, "A", alt_key="coil_area", default=0.01)
    I_max_val = _get_field(em_raw, "I_max", alt_key="max_current", default=1.0)

    electromagnetic = SatelliteCoilsConfiguration(
        N=int(N_val),
        A=float(A_val),
        I_max=float(I_max_val),
    )

    # 4. Sekcja Reaction Wheels
    rw_raw = _get_field(data, "reaction_wheels", default={})

    config_val = _get_field(rw_raw, "configuration", default="pyramid")
    count_val = _get_field(rw_raw, "wheel_count", default=4)
    mass_val = _get_field(rw_raw, "wheel_mass", default=0.025)
    radius_val = _get_field(rw_raw, "wheel_radius", default=0.04)
    height_val = _get_field(rw_raw, "wheel_height", default=0.04)
    speed_val = _get_field(rw_raw, "wheel_max_speed", default=3000.0)
    rw_I_val = _get_field(rw_raw, "inertia_tensor", default=np.eye(3))

    reaction_wheels = SatelliteReactionWheelsConfiguration(
        configuration=str(config_val),
        wheel_count=int(count_val),
        wheel_mass=float(mass_val),
        wheel_radius=float(radius_val),
        wheel_height=float(height_val),
        wheel_max_speed=float(speed_val),
        inertia_tensor=np.asarray(rw_I_val, dtype=np.float64),
    )

    return SatelliteConfiguration(
        mechanical=mechanical,
        electromagnetic=electromagnetic,
        reaction_wheels=reaction_wheels,
    )