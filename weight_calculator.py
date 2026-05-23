"""
Weight calculation module.
Implements specific rules for TMT bars, sheets, tubes, and general products.
"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


# Legacy formula — not used in main flow. Products use stored unit_weight_kg.
def calculate_weight_tmt_bar(quantity: float, diameter_mm: float, length_m: float) -> float:
    """
    Calculate total weight for TMT bars.
    Formula:
    Weight per metre = (diameter_mm ^ 2) / 162
    Unit weight = weight per metre * length_m
    Total weight = unit weight * quantity
    """
    if not diameter_mm or not length_m:
        return 0.0
    weight_per_metre = (diameter_mm ** 2) / 162.0
    unit_weight = weight_per_metre * length_m
    total_weight = unit_weight * quantity
    return total_weight


# Legacy formula — not used in main flow. Products use stored unit_weight_kg.
def calculate_weight_sheet(
    quantity: float,
    length_m: float,
    width_m: float,
    thickness_mm: float,
    density_factor: float = 7.85
) -> float:
    """
    Calculate total weight for sheets and plates.
    Formula:
    Weight = length_m * width_m * (thickness_mm / 1000) * density_factor * quantity
    Note: Converting thickness from mm to m for consistent units,
          or keeping in mm if length/width are in mm.
          Here, length and width are assumed in meters for sanity.
    """
    if not length_m or not width_m or not thickness_mm:
        return 0.0

    # length_m is already in metres; width_m is in mm → convert to metres
    length_m_converted = length_m          # already metres
    width_m_converted = width_m / 1000.0  # mm → m
    thickness_m = thickness_mm / 1000.0

    unit_weight = length_m_converted * width_m_converted * thickness_m * density_factor
    total_weight = unit_weight * quantity
    return total_weight


# Legacy formula — not used in main flow. Products use stored unit_weight_kg.
def calculate_weight_tube(
    quantity: float,
    outer_diameter_mm: float,
    thickness_mm: float,
    length_m: float,
    density: float = 7850.0  # kg/m^3
) -> float:
    """
    Calculate total weight for steel tubes/pipes.
    Formula for hollow cylinder:
    Cross-sectional area (m2) = pi/4 * (OD^2 - (OD - 2t)^2)
    Volume per meter (m3/m) = Cross-sectional area (m2) * 1 (m)
    Unit weight (kg/m) = Volume per meter (m3/m) * density (kg/m3)
    Total weight = Unit weight * length_m * quantity
    """
    import math
    if not outer_diameter_mm or not thickness_mm or not length_m:
        return 0.0

    od_m = outer_diameter_mm / 1000.0
    t_m = thickness_mm / 1000.0

    # Inner diameter
    id_m = od_m - (2 * t_m)
    if id_m < 0:
        id_m = 0

    cross_sectional_area = (math.pi / 4) * (od_m**2 - id_m**2)
    unit_weight = cross_sectional_area * density

    total_weight = unit_weight * length_m * quantity
    return total_weight


def calculate_weight_from_alias(product: Dict, quantity: float) -> float:
    if quantity is None or quantity <= 0:
        return 0.0
    unit_weight_kg = product.get("unit_weight_kg") or 0.0
    if unit_weight_kg <= 0:
        return 0.0
    return round(unit_weight_kg * quantity, 3)
