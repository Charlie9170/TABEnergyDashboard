"""Shared color palette for TAB Energy Dashboard."""

# Primary color palette for the dashboard
COLOR_PALETTE = {
    'primary': '#1f77b4',
    'secondary': '#ff7f0e',
    'success': '#2ca02c',
    'warning': '#d62728',
    'info': '#9467bd',
    'dark': '#1a1a1a',
    'light': '#f0f0f0',
}

# Fuel-specific colors for ERCOT fuel mix visualizations
FUEL_COLORS = {
    'coal': '#2c3e50',
    'natural gas': '#3498db',
    'nuclear': '#9b59b6',
    'wind': '#27ae60',
    'solar': '#f39c12',
    'hydro': '#16a085',
    'other': '#95a5a6',
    'biomass': '#8e44ad',
    'petroleum': '#34495e',
}

def get_fuel_color(fuel_type):
    """Get color for a specific fuel type.
    
    Args:
        fuel_type: Name of the fuel type
        
    Returns:
        Hex color code for the fuel type
    """
    fuel_lower = fuel_type.lower()
    return FUEL_COLORS.get(fuel_lower, COLOR_PALETTE['info'])
