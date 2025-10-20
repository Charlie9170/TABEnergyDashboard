"""Data loading utilities for TAB Energy Dashboard."""

import pandas as pd
from pathlib import Path
from datetime import datetime

# Define the schema for fuel mix data
FUEL_MIX_SCHEMA = {
    'period': 'datetime64[ns]',
    'fuel': 'str',
    'value_mwh': 'float64',
    'last_updated': 'datetime64[ns]'
}

def get_fuel_mix_schema():
    """Get the schema for fuel mix data.
    
    Returns:
        Dictionary with column names and data types
    """
    return FUEL_MIX_SCHEMA.copy()

def load_fuel_mix_data(data_path=None):
    """Load ERCOT fuel mix data from parquet file.
    
    Args:
        data_path: Path to the parquet file. If None, uses default location.
        
    Returns:
        DataFrame with fuel mix data matching the schema
    """
    if data_path is None:
        base_dir = Path(__file__).parent.parent.parent
        data_path = base_dir / 'data' / 'ercot_fuel_mix.parquet'
    else:
        data_path = Path(data_path)
    
    if not data_path.exists():
        # Return empty DataFrame with correct schema if file doesn't exist
        df = pd.DataFrame(columns=list(FUEL_MIX_SCHEMA.keys()))
        for col, dtype in FUEL_MIX_SCHEMA.items():
            df[col] = df[col].astype(dtype)
        return df
    
    try:
        df = pd.read_parquet(data_path)
        
        # Validate and convert columns to match schema
        for col, dtype in FUEL_MIX_SCHEMA.items():
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")
            df[col] = df[col].astype(dtype)
        
        return df
    except Exception as e:
        raise ValueError(f"Error loading fuel mix data: {str(e)}")

def save_fuel_mix_data(df, data_path=None):
    """Save fuel mix data to parquet file.
    
    Args:
        df: DataFrame with fuel mix data
        data_path: Path to save the parquet file. If None, uses default location.
    """
    if data_path is None:
        base_dir = Path(__file__).parent.parent.parent
        data_path = base_dir / 'data' / 'ercot_fuel_mix.parquet'
    else:
        data_path = Path(data_path)
    
    # Ensure directory exists
    data_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Validate schema before saving
    for col, dtype in FUEL_MIX_SCHEMA.items():
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")
    
    df.to_parquet(data_path, index=False)
