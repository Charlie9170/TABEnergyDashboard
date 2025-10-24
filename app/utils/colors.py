"""
Color palette and fuel type mappings for consistent visualization across the dashboard.

Defines the standard color scheme for fuel types used in all charts and maps,
ensuring visual consistency throughout the application.
"""

# TAB-Compliant Color Palette - Professional colors matching TAB brand identity
# Core TAB colors: Navy #1B365D, Red #C8102E, with complementary professional tones
FUEL_COLORS_HEX = {
    "GAS": "#C8102E",      # TAB Red - Natural Gas (dominant fuel in Texas)
    "NATURAL GAS": "#C8102E",  # Alias
    "COAL": "#4A5568",     # Slate Gray - Coal
    "NUCLEAR": "#7C3AED",  # Deep Purple - Nuclear
    "SOLAR": "#F59E0B",    # Amber Gold - Solar Energy
    "SUN": "#F59E0B",      # Alias for Solar
    "WIND": "#1B365D",     # TAB Navy - Wind Energy (major Texas resource)
    "HYDRO": "#0EA5E9",    # Sky Blue - Hydroelectric
    "STORAGE": "#3B82F6",  # Professional Blue - Battery Storage
    "BATTERY STORAGE": "#3B82F6",  # Alias
    "OIL": "#DC2626",      # Crimson Red - Petroleum/Oil
    "BIOMASS": "#059669",  # Forest Green - Biomass
    "OTHER": "#64748B",    # Cool Gray - Other/Unknown
    "UNKNOWN ENERGY STORAGE": "#9CA3AF",  # Light Gray
}


def get_fuel_color_hex(fuel_type: str) -> str:
    """
    Get hex color for a fuel type, with fallback to OTHER.
    
    Args:
        fuel_type: Fuel type name (case-insensitive)
        
    Returns:
        Hex color string (e.g., '#fb923c')
    """
    # Normalize fuel type and handle variations
    fuel_normalized = fuel_type.upper().strip()
    
    # Handle fuel type variations
    if "SOLAR" in fuel_normalized or "SUN" in fuel_normalized:
        return FUEL_COLORS_HEX["SOLAR"]
    elif "WIND" in fuel_normalized:
        return FUEL_COLORS_HEX["WIND"] 
    elif "GAS" in fuel_normalized or "NATURAL GAS" in fuel_normalized:
        return FUEL_COLORS_HEX["GAS"]
    elif "BATTERY" in fuel_normalized or "STORAGE" in fuel_normalized:
        return FUEL_COLORS_HEX["STORAGE"]
    elif "DIESEL" in fuel_normalized or "OIL" in fuel_normalized:
        return FUEL_COLORS_HEX["OIL"]
    elif "UNKNOWN" in fuel_normalized and "STORAGE" in fuel_normalized:
        return FUEL_COLORS_HEX.get("UNKNOWN ENERGY STORAGE", FUEL_COLORS_HEX["OTHER"])
    
    # Direct lookup for exact matches
    return FUEL_COLORS_HEX.get(fuel_normalized, FUEL_COLORS_HEX["OTHER"])


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
