"""
Data loading utilities with validation and caching.

Provides cached data loaders that:
- Read parquet files from the data directory
- Normalize column names using schema aliases
- Coerce types to match canonical schemas
- Validate required columns are present
- Show clear error messages if validation fails
"""

import logging
import streamlit as st
import pandas as pd
from pathlib import Path

from .schema import normalize_columns, coerce_types, validate, get_schema

logger = logging.getLogger(__name__)


def get_data_path(filename: str) -> Path:
    """
    Get absolute path to data file.
    
    Args:
        filename: Name of the data file (e.g., 'fuelmix.parquet')
        
    Returns:
        Path object pointing to the data file
    """
    # Get the project root (parent of app directory)
    project_root = Path(__file__).parent.parent.parent
    return project_root / "data" / filename


@st.cache_data(ttl=3600)  # Cache for 1 hour
def load_parquet(filename: str, dataset: str, allow_empty: bool = False) -> pd.DataFrame:
    """
    Load and validate a parquet file with caching and graceful error handling.
    
    This function:
    1. Loads the parquet file from the data directory
    2. Normalizes column names using schema aliases
    3. Coerces types to match the canonical schema
    4. Validates required columns are present
    5. Returns empty DataFrame with proper schema if file missing (production-safe)
    
    Args:
        filename: Name of the parquet file (e.g., 'fuelmix.parquet')
        dataset: Dataset type for schema validation (e.g., 'fuelmix')
        allow_empty: If True, return empty DataFrame on error instead of stopping
        
    Returns:
        Validated DataFrame with canonical column names and types
        Returns empty DataFrame with schema if file not found and allow_empty=True
        
    Raises:
        Stops Streamlit app execution if file not found or validation fails (unless allow_empty=True)
    """
    filepath = get_data_path(filename)
    
    # Check if file exists
    if not filepath.exists():
        logger.warning("Data file not found: %s (dataset=%s, path=%s)", filename, dataset, filepath)
        st.warning("Data temporarily unavailable.")
        # Return empty DataFrame with proper schema (NEVER use st.stop())
        schema = get_schema(dataset)
        return pd.DataFrame(columns=list(schema.keys()))
    
    try:
        # Load parquet file
        df = pd.read_parquet(filepath)
        
        # Handle completely empty files
        if len(df) == 0:
            logger.warning("Data file is empty: %s (dataset=%s)", filename, dataset)
            st.warning("No data available for this view.")
            # Return empty DataFrame (NEVER use st.stop())
            return df
        
        # Normalize column names
        df = normalize_columns(df, dataset)
        
        # Coerce types
        df = coerce_types(df, dataset)
        
        # Validate schema
        missing, extra = validate(df, dataset)
        
        if missing:
            # Graceful degradation: Show error but DON'T stop entire app
            logger.error(
                "Schema validation failed for %s (dataset=%s): missing=%s, expected=%s, found=%s",
                filename, dataset, missing, list(get_schema(dataset).keys()), list(df.columns),
            )
            st.warning("Some data is temporarily unavailable.")

            if allow_empty:
                return df  # Return partial data
            else:
                # Return empty DataFrame with proper schema instead of st.stop()
                schema = get_schema(dataset)
                return pd.DataFrame(columns=list(schema.keys()))
        
        if extra:
            # Extra columns are okay, just show info (only in debug mode)
            pass  # Silent for production
        
        return df
        
    except pd.errors.ParserError:
        logger.exception("Failed to parse data file %s (dataset=%s)", filename, dataset)
        st.warning("Data temporarily unavailable.")
        # Return empty DataFrame (NEVER use st.stop())
        schema = get_schema(dataset)
        return pd.DataFrame(columns=list(schema.keys()))

    except Exception:
        logger.exception("Unexpected error loading %s (dataset=%s)", filename, dataset)
        st.warning("Data temporarily unavailable.")
        # Return empty DataFrame (NEVER use st.stop())
        schema = get_schema(dataset)
        return pd.DataFrame(columns=list(schema.keys()))


def get_last_updated(df: pd.DataFrame) -> str:
    """
    Extract last_updated timestamp from dataframe with error handling.
    
    Args:
        df: DataFrame with 'last_updated' column
        
    Returns:
        Last updated timestamp as string, or 'Unknown' if not found
    """
    try:
        if df is None or len(df) == 0:
            return 'No data available'
            
        if 'last_updated' in df.columns:
            # Get the first non-null last_updated value
            non_null_values = df['last_updated'].dropna()
            if len(non_null_values) > 0:
                return str(non_null_values.iloc[0])
        
        return 'Unknown'
    except Exception:
        logger.exception("Failed to read last_updated from dataframe")
        return 'Unavailable'
