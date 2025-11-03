"""
Data loading utilities with validation and caching.

Provides cached data loaders that:
- Read parquet files from the data directory
- Normalize column names using schema aliases
- Coerce types to match canonical schemas
- Validate required columns are present
- Show clear error messages if validation fails
"""

import streamlit as st
import pandas as pd
from pathlib import Path

from .schema import normalize_columns, coerce_types, validate, get_schema


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
def load_parquet(filename: str, dataset: str) -> pd.DataFrame:
    """
    Load and validate a parquet file with caching.

    This function:
    1. Loads the parquet file from the data directory
    2. Normalizes column names using schema aliases
    3. Coerces types to match the canonical schema
    4. Validates required columns are present
    5. Shows error message and stops if validation fails

    Args:
        filename: Name of the parquet file (e.g., 'fuelmix.parquet')
        dataset: Dataset type for schema validation (e.g., 'fuelmix')

    Returns:
        Validated DataFrame with canonical column names and types

    Raises:
        Stops Streamlit app execution if file not found or validation fails
    """
    filepath = get_data_path(filename)

    # Check if file exists
    if not filepath.exists():
        st.error(f"❌ Data file not found: `{filepath}`")
        st.info(f"Expected schema for `{dataset}`: {get_schema(dataset)}")
        st.info("Please run the ETL scripts to generate data files.")
        st.stop()

    try:
        # Load parquet file
        df = pd.read_parquet(filepath)

        # Normalize column names
        df = normalize_columns(df, dataset)

        # Coerce types
        df = coerce_types(df, dataset)

        # Validate schema
        missing, extra = validate(df, dataset)

        if missing:
            st.error(f"❌ Missing required columns in `{filename}`: {missing}")
            st.info(f"Expected schema: {get_schema(dataset)}")
            st.info(f"Found columns: {list(df.columns)}")
            st.stop()

        if extra:
            # Extra columns are okay, just show info
            st.info(f"ℹ️ Extra columns in `{filename}` (ignored): {extra}")

        return df

    except Exception as e:
        st.error(f"❌ Error loading `{filename}`: {str(e)}")
        st.stop()


def get_last_updated(df: pd.DataFrame) -> str:
    """
    Extract last_updated timestamp from dataframe.

    Args:
        df: DataFrame with 'last_updated' column

    Returns:
        Last updated timestamp as string, or 'Unknown' if not found
    """
    if 'last_updated' in df.columns and len(df) > 0:
        # Get the first non-null last_updated value
        last_updated = df['last_updated'].dropna().iloc[0] if len(df['last_updated'].dropna()) > 0 else 'Unknown'
        return str(last_updated)
    return 'Unknown'
