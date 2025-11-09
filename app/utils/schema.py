"""
Canonical data schemas and validation utilities.

Defines the expected structure for each dataset and provides functions to:
- Normalize column names from various data sources
- Coerce data types to match schema requirements
- Validate that dataframes have required columns
"""

from typing import Dict, List, Tuple
import pandas as pd

# Canonical schemas for each dataset
# Format: dataset_name -> {column_name: expected_dtype}
SCHEMAS = {
    "fuelmix": {
        "period": "datetime64[ns, UTC]",
        "fuel": "object",
        "value_mwh": "float64",
        "last_updated": "object",
    },
    "price_map": {
        "node_id": "object",
        "lat": "float64",
        "lon": "float64",
        "price_cperkwh": "float64",
        "region": "object",
        "last_updated": "object",
    },
    "generation": {
        "plant_name": "object",
        "lat": "float64",
        "lon": "float64",
        "capacity_mw": "float64",
        "fuel": "object",
        "last_updated": "object",
    },
    "queue": {
        "project_name": "object",
        "lat": "float64",
        "lon": "float64",
        "proposed_mw": "float64",
        "fuel": "object",
        "status": "object",
        "last_updated": "object",
    },
    "minerals": {
        "deposit_name": "object",
        "lat": "float64",
        "lon": "float64",
        "minerals": "object",
        "estimated_tonnage": "float64",
        "development_status": "object",
        "county": "object",
        "details": "object",
        "color": "object",
        "radius": "float64",
        "tooltip": "object",
        "data_source": "object",
        "last_updated": "object",
    },
}

# Column name aliases for normalization
# Maps common alternative names to canonical names
COLUMN_ALIASES = {
    "fuelmix": {
        "type": "fuel",
        "type-name": "fuel",
        "value": "value_mwh",
        "datetime": "period",
        "timestamp": "period",
    },
    "price_map": {
        "node": "node_id",
        "latitude": "lat",
        "longitude": "lon",
        "price": "price_cperkwh",
    },
    "generation": {
        "name": "plant_name",
        "latitude": "lat",
        "longitude": "lon",
        "capacity": "capacity_mw",
        "type": "fuel",
    },
    "queue": {
        "name": "project_name",
        "project": "project_name",
        "latitude": "lat",
        "longitude": "lon",
        "capacity": "proposed_mw",
        "capacity_mw": "proposed_mw",
        "nameplate_mw": "proposed_mw",
        "mw": "proposed_mw",
        "type": "fuel",
    },
    "minerals": {
        "name": "deposit_name",
        "site_name": "deposit_name",
        "latitude": "lat",
        "longitude": "lon",
        "mineral_list": "minerals",
        "tonnage": "estimated_tonnage",
        "status": "development_status",
    },
}


def normalize_columns(df: pd.DataFrame, dataset: str) -> pd.DataFrame:
    """
    Normalize column names using aliases for the given dataset.
    
    Args:
        df: Input dataframe
        dataset: Dataset name (e.g., 'fuelmix', 'price_map')
        
    Returns:
        DataFrame with normalized column names
    """
    if dataset not in COLUMN_ALIASES:
        return df
    
    # Apply aliases to rename columns
    aliases = COLUMN_ALIASES[dataset]
    rename_map = {col: aliases.get(col, col) for col in df.columns}
    return df.rename(columns=rename_map)


def coerce_types(df: pd.DataFrame, dataset: str) -> pd.DataFrame:
    """
    Coerce dataframe columns to match schema types.
    
    Args:
        df: Input dataframe
        dataset: Dataset name (e.g., 'fuelmix', 'price_map')
        
    Returns:
        DataFrame with coerced types
    """
    if dataset not in SCHEMAS:
        return df
    
    schema = SCHEMAS[dataset]
    df = df.copy()
    
    for col, dtype in schema.items():
        if col in df.columns:
            try:
                if dtype == "datetime64[ns, UTC]":
                    # Handle datetime conversion with UTC timezone
                    df[col] = pd.to_datetime(df[col], utc=True)
                elif dtype == "float64":
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                elif dtype == "object":
                    df[col] = df[col].astype(str)
            except Exception as e:
                print(f"Warning: Could not coerce column {col} to {dtype}: {e}")
    
    return df


def validate(df: pd.DataFrame, dataset: str) -> Tuple[List[str], List[str]]:
    """
    Validate that dataframe has required columns.
    
    Args:
        df: Input dataframe
        dataset: Dataset name (e.g., 'fuelmix', 'price_map')
        
    Returns:
        Tuple of (missing_columns, extra_columns)
    """
    if dataset not in SCHEMAS:
        return [], []
    
    required_cols = set(SCHEMAS[dataset].keys())
    actual_cols = set(df.columns)
    
    missing = list(required_cols - actual_cols)
    extra = list(actual_cols - required_cols)
    
    return missing, extra


def get_schema(dataset: str) -> Dict[str, str]:
    """
    Get the canonical schema for a dataset.
    
    Args:
        dataset: Dataset name (e.g., 'fuelmix', 'price_map')
        
    Returns:
        Dictionary mapping column names to data types
    """
    return SCHEMAS.get(dataset, {})
