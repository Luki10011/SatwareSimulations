import numpy as np
from dataclasses import dataclass
from typing import Any, Dict, List

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
COIL_AREA_MAX = 0.25    # m^2

MAX_CURRENT_MIN = 0.01  # A
MAX_CURRENT_MAX = 10.0  # A


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
    com_offset: np.ndarray    # offset of wheel assembly COM [m]
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


def calculate_reaction_wheel_inertia_tensor(wheel_mass: float, wheel_radius: float, wheel_height: float) -> np.ndarray:
    """Return the inertia tensor of a thin cylindrical wheel about its own center."""
    if wheel_mass <= 0.0 or wheel_radius <= 0.0 or wheel_height <= 0.0:
        return np.zeros((3, 3), dtype=float)

    i_xy = 0.25 * wheel_mass * wheel_radius**2
    i_z = 0.5 * wheel_mass * wheel_radius**2
    return np.array(
        [
            [i_xy + wheel_mass * wheel_height**2 / 12.0, 0.0, 0.0],
            [0.0, i_xy + wheel_mass * wheel_height**2 / 12.0, 0.0],
            [0.0, 0.0, i_z],
        ],
        dtype=float,
    )


def calculate_total_inertia_tensor(
    mechanical_tensor: np.ndarray,
    mechanical_mass: float,
    wheel_mass: float,
    wheel_radius: float,
    wheel_height: float,
    wheel_count: int,
    com_offset: np.ndarray,
) -> np.ndarray:
    """Add wheel inertia using Steiner's theorem for a moved center of mass."""
    total = np.array(mechanical_tensor, dtype=float, copy=True)
    wheel_tensor = calculate_reaction_wheel_inertia_tensor(wheel_mass, wheel_radius, wheel_height)

    if wheel_count <= 0:
        return total

    offset = np.array(com_offset, dtype=float)
    offset_sq = float(np.dot(offset, offset))
    total += wheel_count * wheel_tensor
    total += wheel_count * wheel_mass * np.array(
        [
            [offset_sq - offset[0]**2, -offset[0] * offset[1], -offset[0] * offset[2]],
            [-offset[1] * offset[0], offset_sq - offset[1]**2, -offset[1] * offset[2]],
            [-offset[2] * offset[0], -offset[2] * offset[1], offset_sq - offset[2]**2],
        ],
        dtype=float,
    )

    return total


from typing import Dict, Any, List
import numpy as np

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
        if wheel_max_speed <= 0.0:
            errors["wheel_max_speed"] = "Reaction wheel max speed must be greater than zero."

    return errors

def build_satellite_configuration(data: Dict[str, Any]) -> SatelliteConfiguration:
    mechanical = data.get("mechanical", {})
    electromagnetic = data.get("electromagnetic", {})
    reaction_wheels = data.get("reaction_wheels", {})

    dimensions = mechanical.get("dimensions", [0.3, 0.2, 0.1])
    if not isinstance(dimensions, (list, tuple)) or len(dimensions) != 3:
        dimensions = [0.3, 0.2, 0.1]

    inertia_matrix = mechanical.get("inertia_tensor", [[0.02, 0.0, 0.0], [0.0, 0.015, 0.0], [0.0, 0.0, 0.01]])
    inertia_array = np.array(inertia_matrix, dtype=float)

    wheel_mass = _coerce_float(reaction_wheels.get("wheel_mass"), 0.25)
    wheel_radius = _coerce_float(reaction_wheels.get("wheel_radius"), 0.05)
    wheel_height = _coerce_float(reaction_wheels.get("wheel_height"), 0.02)
    wheel_max_speed = _coerce_float(reaction_wheels.get("wheel_max_speed"), 6000.0)
    com_offset = np.array(reaction_wheels.get("com_offset", [0.003, 0.002, 0.001]), dtype=float)

    wheel_tensor = calculate_reaction_wheel_inertia_tensor(wheel_mass, wheel_radius, wheel_height)
    total_tensor = calculate_total_inertia_tensor(
        mechanical_tensor=inertia_array,
        mechanical_mass=_coerce_float(mechanical.get("mass"), 12.5),
        wheel_mass=wheel_mass,
        wheel_radius=wheel_radius,
        wheel_height=wheel_height,
        wheel_count=_coerce_int(reaction_wheels.get("wheel_count"), 3),
        com_offset=com_offset,
    )

    return SatelliteConfiguration(
        mechanical=SatelliteMechanicalConfiguration(
            m=_coerce_float(mechanical.get("mass"), 12.5),
            I=total_tensor,
            a=_coerce_float(dimensions[0], 0.3),
            b=_coerce_float(dimensions[1], 0.2),
            h=_coerce_float(dimensions[2], 0.1),
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
            com_offset=com_offset,
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
            "com_offset": config.reaction_wheels.com_offset.tolist(),
            "inertia_tensor": config.reaction_wheels.inertia_tensor.tolist(),
        },
    }