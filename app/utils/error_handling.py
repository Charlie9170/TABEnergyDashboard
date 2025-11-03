"""
Dashboard utilities for error handling and data validation.

Provides standardized functions for:
- Graceful error handling across all tabs
- Data validation and schema checking
- Safe DataFrame operations with fallbacks
- Consistent user messaging
"""

import streamlit as st
import pandas as pd
from typing import Optional, List, Dict, Any
import logging


def safe_dataframe_operation(func, fallback_value=None, error_message: str = "Data processing error"):
    """
    Safely execute a DataFrame operation with error handling.

    Args:
        func: Function to execute
        fallback_value: Value to return if operation fails
        error_message: Error message to display to user

    Returns:
        Result of func() or fallback_value if error occurs
    """
    try:
        return func()
    except Exception as e:
        st.error(f"{error_message}: {str(e)}")
        logging.error(f"{error_message}: {str(e)}")
        return fallback_value


def validate_dataframe_columns(df: pd.DataFrame, required_columns: List[str], tab_name: str = "Tab") -> bool:
    """
    Validate that a DataFrame has required columns.

    Args:
        df: DataFrame to validate
        required_columns: List of required column names
        tab_name: Name of the tab for error messaging

    Returns:
        True if all required columns exist, False otherwise
    """
    if df.empty:
        st.warning(f"{tab_name}: No data available.")
        return False

    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        st.error(f"{tab_name}: Missing required columns: {', '.join(missing_columns)}")
        st.info(f"Available columns: {', '.join(df.columns.tolist())}")
        return False

    return True


def safe_numeric_operation(value, fallback: float = 0.0, operation: str = "calculation") -> float:
    """
    Safely convert value to float with fallback.

    Args:
        value: Value to convert
        fallback: Fallback value if conversion fails
        operation: Description of operation for logging

    Returns:
        Float value or fallback
    """
    try:
        if pd.isna(value):
            return fallback
        return float(value)
    except (ValueError, TypeError):
        logging.warning(f"Failed {operation} with value {value}, using fallback {fallback}")
        return fallback


def safe_groupby_operation(df: pd.DataFrame, groupby_cols: List[str], agg_col: str,
                           agg_func: str = 'sum', fallback_dict: Optional[Dict] = None) -> pd.Series:
    """
    Safely perform groupby operations with error handling.

    Args:
        df: DataFrame to group
        groupby_cols: Columns to group by
        agg_col: Column to aggregate
        agg_func: Aggregation function name
        fallback_dict: Fallback dictionary if operation fails

    Returns:
        Grouped Series or empty Series with fallback data
    """
    try:
        if df.empty:
            return pd.Series(fallback_dict or {})

        result = df.groupby(groupby_cols)[agg_col].agg(agg_func)
        return result if not result.empty else pd.Series(fallback_dict or {})

    except Exception as e:
        logging.error(f"Groupby operation failed: {str(e)}")
        return pd.Series(fallback_dict or {})


def create_safe_tooltip_data(df: pd.DataFrame, tooltip_columns: List[str]) -> pd.DataFrame:
    """
    Safely prepare DataFrame for tooltip display by ensuring all columns exist and are strings.

    Args:
        df: Source DataFrame
        tooltip_columns: List of columns needed for tooltips

    Returns:
        DataFrame with safe tooltip data
    """
    df_tooltip = df.copy()

    for col in tooltip_columns:
        if col not in df_tooltip.columns:
            df_tooltip[col] = "N/A"
        else:
            # Convert to string and handle NaN values
            df_tooltip[col] = df_tooltip[col].fillna("N/A").astype(str)

    return df_tooltip


def render_error_boundary(tab_name: str, error: Exception, show_details: bool = False):
    """
    Render a standardized error boundary for tabs.

    Args:
        tab_name: Name of the tab where error occurred
        error: Exception that was caught
        show_details: Whether to show detailed error information
    """
    st.error(f"⚠️ {tab_name} Error")

    with st.expander("Error Details", expanded=show_details):
        st.code(str(error))

    st.markdown("""
    **Possible Solutions:**
    - Refresh the page to retry loading
    - Check if data files exist in the `data/` directory
    - Run the ETL scripts to regenerate data
    - Contact support if the issue persists
    """)


def validate_map_data(df: pd.DataFrame, required_cols: List[str]) -> Optional[pd.DataFrame]:
    """
    Validate and clean data for map rendering.

    Args:
        df: DataFrame to validate
        required_cols: Required columns for mapping

    Returns:
        Cleaned DataFrame or None if validation fails
    """
    if not validate_dataframe_columns(df, required_cols, "Map"):
        return None

    # Filter out rows with invalid coordinates
    if 'lat' in df.columns and 'lon' in df.columns:
        df_clean = df.copy()
        df_clean['lat'] = pd.to_numeric(df_clean['lat'], errors='coerce')
        df_clean['lon'] = pd.to_numeric(df_clean['lon'], errors='coerce')

        # Remove rows with invalid coordinates
        valid_coords = df_clean['lat'].notna() & df_clean['lon'].notna()
        df_clean = df_clean[valid_coords]

        if df_clean.empty:
            st.warning("No valid coordinates found for mapping.")
            return None

        return df_clean

    return df


def log_dashboard_event(event: str, tab: str, details: Optional[Dict[str, Any]] = None):
    """
    Log dashboard events for monitoring and debugging.

    Args:
        event: Event type (e.g., 'data_load', 'error', 'render')
        tab: Tab name where event occurred
        details: Additional event details
    """
    log_entry = {
        'event': event,
        'tab': tab,
        'details': details or {}
    }
    logging.info(f"Dashboard event: {log_entry}")
