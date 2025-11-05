"""
Data loading utilities with validation and caching.

Provides cached data loaders that:
- Read parquet files from the data directory
- Normalize column names using schema aliases
- Coerce types to match canonical schemas
- Validate required columns are present
- Show clear error messages if validation fails
"""

import os
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
        error_msg = f"❌ Data file not found: `{filename}`"
        if allow_empty:
            st.warning(error_msg)
            st.info("🔄 Displaying with empty data. Run ETL scripts to populate.")
            # Return empty DataFrame with proper schema
            schema = get_schema(dataset)
            return pd.DataFrame(columns=list(schema.keys()))
        else:
            st.error(error_msg)
            st.info(f"Expected schema for `{dataset}`: {get_schema(dataset)}")
            st.info("Please run the ETL scripts to generate data files.")
            st.stop()
    
    try:
        # Load parquet file
        df = pd.read_parquet(filepath)
        
        # Handle completely empty files
        if len(df) == 0:
            if allow_empty:
                st.warning(f"⚠️ Data file `{filename}` is empty")
                st.info("🔄 Run ETL scripts to populate with fresh data.")
                return df
            else:
                st.error(f"❌ Data file `{filename}` is empty")
                st.info("Please run the ETL scripts to generate data.")
                st.stop()
        
        # Normalize column names
        df = normalize_columns(df, dataset)
        
        # Coerce types
        df = coerce_types(df, dataset)
        
        # Validate schema
        missing, extra = validate(df, dataset)
        
        if missing:
            error_msg = f"❌ Missing required columns in `{filename}`: {missing}"
            if allow_empty:
                st.warning(error_msg)
                st.info(f"Expected: {get_schema(dataset)}")
                st.info("🔄 Using partial data. Some features may not work.")
                return df  # Return partial data
            else:
                st.error(error_msg)
                st.info(f"Expected schema: {get_schema(dataset)}")
                st.info(f"Found columns: {list(df.columns)}")
                st.stop()
        
        if extra:
            # Extra columns are okay, just show info (only in debug mode)
            pass  # Silent for production
        
        return df
        
    except pd.errors.ParserError as e:
        error_msg = f"❌ Corrupted data file `{filename}`: {str(e)}"
        if allow_empty:
            st.error(error_msg)
            st.info("🔄 File may be corrupted. Try re-running ETL scripts.")
            schema = get_schema(dataset)
            return pd.DataFrame(columns=list(schema.keys()))
        else:
            st.error(error_msg)
            st.stop()
            
    except Exception as e:
        error_msg = f"❌ Unexpected error loading `{filename}`: {str(e)}"
        if allow_empty:
            st.error(error_msg)
            st.info("🔄 Please check the data file and ETL scripts.")
            schema = get_schema(dataset)
            return pd.DataFrame(columns=list(schema.keys()))
        else:
            st.error(error_msg)
            st.stop()


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
    except Exception as e:
        return f'Error: {str(e)}'


def get_file_modification_time(filename: str) -> str:
    """
    Get the last modification time of a data file.
    
    Args:
        filename: Name of the data file (e.g., 'fuelmix.parquet')
        
    Returns:
        Last modification time as formatted string, or 'Unknown' if error
    """
    try:
        filepath = get_data_path(filename)
        if filepath.exists():
            import datetime
            mod_time = datetime.datetime.fromtimestamp(filepath.stat().st_mtime)
            return mod_time.strftime("%Y-%m-%d %H:%M:%S")
        return 'File not found'
    except Exception as e:
        return f'Error: {str(e)}'
