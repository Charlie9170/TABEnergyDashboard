"""
Color palette and fuel type mappings for consistent visualization across the dashboard.

Defines the standard color scheme for fuel types used in all charts and maps,
ensuring visual consistency throughout the application.
"""

# ================================
# TAB DESIGN SYSTEM - COLOR TOKENS
# ================================
# Professional color palette matching TAB brand identity and design system
# Ensures WCAG AA accessibility (4.5:1 contrast ratio minimum)

# Core TAB Brand Colors
TAB_COLORS = {
    "primary": "#1B365D",      # TAB Navy - Brand primary
    "accent": "#C8102E",       # TAB Red - Brand accent
    "success": "#059669",      # Emerald Green - Success states
    "warning": "#F59E0B",      # Amber - Warning states
    "info": "#3B82F6",         # Blue - Info states
}

# Neutral Palette
NEUTRAL_COLORS = {
    "text": "#0F172A",         # Slate 900 - Primary text
    "text_muted": "#64748B",   # Slate 500 - Secondary text
    "text_light": "#94A3B8",   # Slate 400 - Tertiary text
    "border": "#E2E8F0",       # Slate 200 - Borders
    "surface": "#F8FAFC",      # Slate 50 - Cards/surfaces
    "background": "#FFFFFF",   # White - Page background
}

# Fuel Type Color Palette - TAB Brand Colors Only
# Two main colors match TAB logo exactly: Navy #1B365D and Red #C8102E
# Supporting colors use lighter grays and complementary muted blues
FUEL_COLORS_HEX = {
    # Two largest fuel sources - EXACT TAB logo colors
    "GAS": "#C8102E",          # TAB Red - Natural Gas (EXACT logo red)
    "NATURAL GAS": "#C8102E",  # Alias
    "WIND": "#1B365D",         # TAB Navy - Wind (EXACT logo navy)
    
    # Supporting sources - Complementary to TAB colors
    "NUCLEAR": "#A0102E",      # Dark Maroon (TAB Red variation)
    "COAL": "#4A6B8A",         # Soft Blue-Gray (complementary to TAB Navy, lighter)
    "SOLAR": "#E8EAED",        # Very Light Gray (nearly white)
    "SUN": "#E8EAED",          # Alias for Solar
    
    # Smaller sources - Near-whites and subtle blues
    "HYDRO": "#F0F1F3",        # Off-White (very light)
    "STORAGE": "#64748B",      # Slate Blue - Subtle, professional
    "BATTERY STORAGE": "#64748B",  # Alias - Slate Blue
    "OIL": "#6B8CAE",          # Soft Slate Blue (complementary, muted)
    "BIOMASS": "#F3F4F6",      # Near White
    
    # Catchall
    "OTHER": "#F8F9FA",        # Almost White
    "UNKNOWN ENERGY STORAGE": "#FCFCFD",  # Pure White tint
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
