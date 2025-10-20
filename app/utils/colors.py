"""
Color palette and fuel type mappings for consistent visualization across the dashboard.

Defines the standard color scheme for fuel types used in all charts and maps,
ensuring visual consistency throughout the application.
"""

# Standard fuel color palette (hex values)
FUEL_COLORS_HEX = {
    "GAS": "#fb923c",      # Orange - Natural Gas
    "WIND": "#14b8a6",     # Teal - Wind Energy
    "SOLAR": "#eab308",    # Yellow - Solar Energy
    "SUN": "#eab308",      # Alias for Solar
    "COAL": "#6b7280",     # Gray - Coal
    "NUCLEAR": "#9333ea",  # Purple - Nuclear
    "STORAGE": "#3b82f6",  # Blue - Battery Storage
    "HYDRO": "#06b6d4",    # Cyan - Hydroelectric
    "BIOMASS": "#84cc16",  # Lime - Biomass
    "OTHER": "#64748b",    # Slate - Other/Unknown
}


def get_fuel_color_hex(fuel_type: str) -> str:
    """
    Get hex color for a fuel type, with fallback to OTHER.
    
    Args:
        fuel_type: Fuel type name (case-insensitive)
        
    Returns:
        Hex color string (e.g., '#fb923c')
    """
    return FUEL_COLORS_HEX.get(fuel_type.upper(), FUEL_COLORS_HEX["OTHER"])


def get_fuel_color_rgb(fuel_type: str) -> list:
    """
    Get RGB color array for fuel type (for pydeck).
    
    Args:
        fuel_type: Fuel type name (case-insensitive)
        
    Returns:
        RGB list [r, g, b] with values 0-255
    """
    hex_color = get_fuel_color_hex(fuel_type)
    # Remove '#' and convert hex to RGB
    hex_color = hex_color.lstrip('#')
    return [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]


def get_fuel_color_rgba(fuel_type: str, alpha: int = 255) -> list:
    """
    Get RGBA color array for fuel type (for pydeck with transparency).
    
    Args:
        fuel_type: Fuel type name (case-insensitive)
        alpha: Alpha channel value 0-255 (default 255 = opaque)
        
    Returns:
        RGBA list [r, g, b, a] with values 0-255
    """
    rgb = get_fuel_color_rgb(fuel_type)
    return rgb + [alpha]


# Renewable fuel types for calculating renewable share
RENEWABLE_FUELS = {"WIND", "SUN", "SOLAR", "HYDRO", "BIOMASS"}


def is_renewable(fuel_type: str) -> bool:
    """
    Check if a fuel type is considered renewable.
    
    Args:
        fuel_type: Fuel type name (case-insensitive)
        
    Returns:
        True if renewable, False otherwise
    """
    return fuel_type.upper() in RENEWABLE_FUELS
