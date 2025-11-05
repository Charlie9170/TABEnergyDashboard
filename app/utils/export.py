"""
Data Export Utilities

Provides standardized CSV export functionality for legislative use.
"""

import streamlit as st
import pandas as pd
from datetime import datetime


def create_download_button(df: pd.DataFrame, filename_prefix: str, label: str = "Download Data (CSV)") -> None:
    """
    Create standardized download button for dataframes.
    
    Generates timestamped CSV files for use in presentations, reports,
    and policy briefings by TAB members and legislators.
    
    Args:
        df: DataFrame to export
        filename_prefix: Prefix for filename (e.g., 'fuelmix', 'generation')
        label: Button label text
    
    Returns:
        None - renders Streamlit download button
    
    Example:
        >>> create_download_button(
        ...     df=generation_data,
        ...     filename_prefix="generation_facilities",
        ...     label="Download Facilities Data"
        ... )
    """
    # Generate timestamp for version tracking
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"tab_energy_{filename_prefix}_{timestamp}.csv"
    
    # Convert to CSV without index
    csv = df.to_csv(index=False)
    
    # Create download button
    st.download_button(
        label=label,
        data=csv,
        file_name=filename,
        mime="text/csv",
        help=f"Download {filename_prefix} data as CSV for use in presentations and policy analysis"
    )


def get_export_info() -> str:
    """
    Get standardized help text for export functionality.
    
    Returns:
        Markdown-formatted help text explaining export feature
    """
    return """
    **Export Data for Legislative Use:**
    - CSV format compatible with Excel and Google Sheets
    - Timestamped filenames for version control
    - Use in committee hearings, policy briefs, and presentations
    - All source data included for reproducibility
    """
