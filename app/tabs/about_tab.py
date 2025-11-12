"""
About & Data Sources Tab

Provides transparency on data sources, methodology, and technical details
for TAB members and policymakers.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
import os

import sys
sys.path.append(str(Path(__file__).parent.parent))

from utils.loaders import get_data_path


def get_file_timestamp(filename: str) -> str:
    """
    Get the last modified timestamp of a data file.
    
    Args:
        filename: Name of the parquet file
        
    Returns:
        Formatted timestamp string or "Not available" if file doesn't exist
    """
    try:
        file_path = get_data_path(filename)
        if file_path.exists():
            timestamp = datetime.fromtimestamp(file_path.stat().st_mtime)
            return timestamp.strftime("%B %d, %Y at %I:%M %p CT")
        else:
            return "Not available"
    except Exception:
        return "Not available"


def render():
    """Render the About & Data Sources tab."""
    
    # Header
    st.markdown("### About & Data Sources")
    st.markdown("Transparency and methodology for the TAB Energy Dashboard")
    
    st.markdown("---")
    
    # Mission Statement
    st.markdown("## Mission")
    st.markdown("""
    **Real-time energy market intelligence for Texas policymakers**
    
    This dashboard provides the Texas Association of Business (TAB) members, legislators, 
    and stakeholders with authoritative, up-to-date insights into the Texas electricity market. 
    All data is sourced from official government agencies and ERCOT public reports.
    
    **How to Use This Dashboard:**
    - Navigate between tabs to explore different aspects of Texas energy markets
    - Each data tab includes a **"Download Data" button** for exporting to CSV
    - CSV files are compatible with Excel, Google Sheets, and other analysis tools
    - Filenames are timestamped for version control and reproducibility
    - Use downloaded data in legislative presentations, policy briefs, and committee hearings
    """)
    
    st.markdown("---")
    
    # Data Sources Section
    st.markdown("## Data Sources & Methodology")
    
    # Create columns for data source cards
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-card-title">ERCOT Fuel Mix</div>
            <div style="margin-top: 0.5rem; font-size: 0.9rem; color: #64748B;">
                <strong>Source:</strong> U.S. Energy Information Administration<br>
                <strong>Dataset:</strong> EIA-930 Real-time Grid Monitor<br>
                <strong>Coverage:</strong> ERCOT hourly generation by fuel type<br>
                <strong>Update Frequency:</strong> Every 6 hours (automated)<br>
                <strong>Last Updated:</strong> {fuelmix_time}
            </div>
        </div>
        """.format(fuelmix_time=get_file_timestamp("fuelmix.parquet")), 
        unsafe_allow_html=True)
        
        st.markdown("")
        
        st.markdown("""
        <div class="metric-card">
            <div class="metric-card-title">Interconnection Queue</div>
            <div style="margin-top: 0.5rem; font-size: 0.9rem; color: #64748B;">
                <strong>Source:</strong> Electric Reliability Council of Texas<br>
                <strong>Dataset:</strong> Capacity, Demand & Reserves (CDR) Report<br>
                <strong>Coverage:</strong> Planned generation projects in pipeline<br>
                <strong>Update Frequency:</strong> Monthly (ERCOT CDR publication)<br>
                <strong>Last Updated:</strong> {queue_time}
            </div>
        </div>
        """.format(queue_time=get_file_timestamp("queue.parquet")), 
        unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-card-title">Generation Facilities</div>
            <div style="margin-top: 0.5rem; font-size: 0.9rem; color: #64748B;">
                <strong>Source:</strong> U.S. Energy Information Administration<br>
                <strong>Dataset:</strong> EIA-860 Operating Generator Capacity<br>
                <strong>Coverage:</strong> Texas power plants ≥1 MW capacity<br>
                <strong>Update Frequency:</strong> Monthly (EIA data releases)<br>
                <strong>Last Updated:</strong> {generation_time}
            </div>
        </div>
        """.format(generation_time=get_file_timestamp("generation.parquet")), 
        unsafe_allow_html=True)
        
        st.markdown("")
        
        st.markdown("""
        <div class="metric-card">
            <div class="metric-card-title">Real-Time Price Map</div>
            <div style="margin-top: 0.5rem; font-size: 0.9rem; color: #64748B;">
                <strong>Source:</strong> ERCOT Public API<br>
                <strong>Dataset:</strong> Real-Time Settlement Point Prices (LMP)<br>
                <strong>Coverage:</strong> ERCOT weather zones (8 zones)<br>
                <strong>Update Frequency:</strong> Every 6 hours via automated ETL<br>
                <strong>Status:</strong> 🟢 Live Data
            </div>
        </div>
        """, unsafe_allow_html=True)
    
        st.markdown("")
    
    # Data Processing Methodology
    with st.expander("📊 Data Processing & Validation"):
        st.markdown("""
        **ETL Pipeline:**
        - Automated Extract-Transform-Load (ETL) scripts fetch data from source APIs
        - Python-based data validation ensures schema compliance
        - Cross-referenced with ERCOT public reports for accuracy
        - Data stored in Parquet format for performance and reliability
        
        **Quality Assurance:**
        - Schema validation on all incoming data
        - Coordinate validation for geographic data (Texas bounds)
        - Fuel type normalization using EIA standard categories
        - Automated error logging and fallback to cached data
        
        **Data Governance:**
        - All data sourced from official government/ERCOT sources
        - No proprietary or confidential data included
        - Open-source processing for transparency
        - Reproducible results from documented pipelines
        """)
    
    # API & Technical Details
    with st.expander("🔌 API Access & Rate Limits"):
        st.markdown("""
        **EIA API:**
        - Rate Limit: 1,000 calls per hour
        - Registration: Free at https://www.eia.gov/opendata/
        - Authentication: API key required
        - Data cached locally for performance
        
        **ERCOT Data:**
        - Source: Public CDR reports (Excel format)
        - No API key required
        - Updated monthly with official ERCOT releases
        
        **Graceful Degradation:**
        - If APIs are unavailable, dashboard falls back to cached data
        - Users notified when viewing cached vs. live data
        - Maximum cache age: 24 hours before warning displayed
        """)
    
    # Technical Architecture
    with st.expander("⚙️ Technical Architecture"):
        st.markdown("""
        **Frontend:**
        - Framework: Streamlit (Python web framework)
        - Visualizations: Plotly (interactive charts), pydeck (maps)
        - Responsive design for desktop and mobile devices
        
        **Backend:**
        - Language: Python 3.11+
        - Data Processing: pandas, pyarrow
        - Storage: Parquet files with Snappy compression
        - Automation: GitHub Actions (scheduled ETL runs)
        
        **Hosting:**
        - Platform: Streamlit Cloud / Local deployment
        - Data Storage: Local file system (Parquet)
        - Updates: Automated via scheduled jobs
        
        **Security:**
        - API keys stored in secrets management (not in code)
        - .gitignore protection for sensitive credentials
        - HTTPS encryption for data transmission
        """)
    
    st.markdown("---")
    
    # About TAB
    st.markdown("## About the Dashboard")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        **Developed by:** Texas Association of Business (TAB)
        
        **Purpose:** To provide data-driven insights for Texas energy policy discussions, 
        enabling informed decision-making by business leaders, legislators, and stakeholders.
        
        **Version:** 1.0 (November 2025)
        
        **Contact:** 
        - Website: [texasbusiness.com](https://www.texasbusiness.com)
        - Email: info@txbiz.org
        - Phone: (512) 477-6721
        """)
    
    with col2:
        st.markdown("""
        <div class="metric-card">
            <div class="metric-card-title">Dashboard Stats</div>
            <div style="margin-top: 0.5rem; font-size: 0.9rem;">
                <strong>Datasets:</strong> 4 live sources<br>
                <strong>Updates:</strong> Every 6 hours<br>
                <strong>Coverage:</strong> All of Texas/ERCOT<br>
                <strong>Status:</strong> Production Ready
            </div>
        </div>
        """, unsafe_allow_html=True)
    
        st.markdown("")
    
        # Data Transparency Statement
        st.info("""
        **Transparency Commitment:** All data displayed in this dashboard comes from official 
        government agencies (U.S. EIA) and ERCOT public reports. The Texas Association of Business 
        does not modify, editorialize, or alter the underlying data. Processing is limited to 
        formatting, aggregation, and validation for display purposes only.
        """)
    
    # Open Source & GitHub
    with st.expander("🔓 Open Source & Documentation"):
        st.markdown("""
        **Source Code:**
        - Repository: [github.com/Charlie9170/TABEnergyDashboard](https://github.com/Charlie9170/TABEnergyDashboard)
        - License: MIT License
        - Contributions: Welcome via pull requests
        
        **Documentation:**
        - Setup Guide: See repository README.md
        - ETL Scripts: Documented in `/etl/` directory
        - Data Schemas: Defined in `/app/utils/schema.py`
        
        **Reproducibility:**
        - All data processing steps are documented
        - ETL scripts can be run independently
        - Results are reproducible with same source data
        """)
    
    st.markdown("---")
    
    # Footer
    st.markdown("""
    <div style="text-align: center; color: #64748B; font-size: 0.85rem; padding: 1rem 0;">
        <strong>Texas Association of Business Energy Dashboard</strong><br>
        Powering policy with data • Built with Streamlit • Data via EIA & ERCOT<br>
        Last page load: {current_time}
    </div>
    """.format(current_time=datetime.now().strftime("%B %d, %Y at %I:%M %p CT")),
    unsafe_allow_html=True)
