"""
Data source tracking and citation utilities.

Provides consistent data source indicators and citations across all dashboard tabs.
Helps users understand which data is real vs. demo/placeholder.
"""

from typing import Dict, Tuple, Optional
import streamlit as st

# Data source registry - tracks status of each dataset
DATA_SOURCES = {
    'fuelmix': {
        'status': 'live',  # live, demo, stub
        'source': 'U.S. Energy Information Administration (EIA)',
        'api': 'EIA v2 API - Electricity RTO Fuel Type Data',
        'respondent': 'ERCO (ERCOT)',
        'update_frequency': 'Every 6 hours via GitHub Actions',
        'url': 'https://www.eia.gov/opendata/',
    },
    'price_map': {
        'status': 'live',
        'source': 'ERCOT Public API',
        'api': 'Real-Time Settlement Point Prices (SPP)',
        'coverage': 'ERCOT weather zones (8 zones)',
        'update_frequency': 'Every 6 hours via automated ETL',
        'url': 'https://www.ercot.com/mp/data-products/data-product-details?id=NP6-785-ER',
    },
    'generation': {
        'status': 'live',
        'source': 'U.S. Energy Information Administration (EIA)',
        'api': 'EIA v2 API - Operating Generator Capacity',
        'coverage': 'Texas power plants ≥1 MW capacity',
        'update_frequency': 'Monthly from EIA (manual ETL execution)',
        'url': 'https://www.eia.gov/opendata/',
    },
    'queue': {
        'status': 'live',
        'source': 'Electric Reliability Council of Texas (ERCOT)',
        'api': 'ERCOT Capacity, Demand and Reserves (CDR) Report',
        'coverage': 'Planned generation projects in interconnection queue',
        'update_frequency': 'Monthly via ERCOT CDR Report publication',
        'url': 'https://www.ercot.com/gridinfo/resource',
        'data_file': 'CapacityDemandandReservesReport_May2025_Revised.xlsx'
    },
    'minerals': {
        'status': 'live',
        'source': 'Manual Curation + Geological Surveys',
        'api': 'Texas General Land Office, USGS, Industry Disclosures',
        'coverage': 'REEs and Critical Minerals deposits in Texas',
        'update_frequency': 'Manual updates as new deposits are discovered',
        'url': 'https://www.glo.texas.gov/',
        'note': 'Data compiled from GLO reports, USGS surveys, and industry announcements'
    }
}

def get_data_status_badge(dataset: str) -> str:
    """
    Get a colored status badge for a dataset.
    
    Args:
        dataset: Dataset name (fuelmix, price_map, generation, queue)
        
    Returns:
        HTML badge indicating data status
    """
    if dataset not in DATA_SOURCES:
        return "❓ **Unknown**"
    
    status = DATA_SOURCES[dataset]['status']
    
    if status == 'live':
        return "🟢 **LIVE DATA**"
    elif status == 'demo':
        return "🟡 **DEMO DATA**"
    elif status == 'stub':
        return "🔴 **NOT IMPLEMENTED**"
    else:
        return "❓ **Unknown Status**"

def render_data_source_footer(dataset: str, last_updated: Optional[str] = None) -> None:
    """
    Render a standardized footer with data source information.
    
    Args:
        dataset: Dataset name for source lookup
        last_updated: Last update timestamp (if available)
    """
    if dataset not in DATA_SOURCES:
        st.error(f"Unknown dataset: {dataset}")
        return
    
    source_info = DATA_SOURCES[dataset]
    status = source_info['status']
    
    # Status indicator
    st.markdown("---")
    
    if status == 'live':
        # Clean, professional footer for live data
        st.markdown(f"""
        **Data Source:** {source_info['source']}  
        **API:** {source_info['api']}  
        **Updates:** {source_info['update_frequency']}  
        {f"**Last Updated:** {last_updated}" if last_updated else ""}
        """)
        
    elif status == 'demo':
        # Red warning box for demo data - intentionally temporary looking
        st.markdown(f"""
        <div style="
            background-color: #fef2f2; 
            border: 3px dashed #dc2626; 
            padding: 15px; 
            border-radius: 8px; 
            margin: 10px 0;
            color: #991b1b;
            font-weight: bold;
        ">
            TEMPORARY DEMO DATA<br>
            <span style="font-size: 0.9em;">This section uses sample data for development only.</span><br>
            <span style="font-size: 0.8em; font-weight: normal;">
                <strong>Will be replaced with:</strong> {source_info['target_source']}<br>
                <strong>Note:</strong> {source_info['note']}
            </span>
        </div>
        """, unsafe_allow_html=True)
        
    elif status == 'stub':
        # Orange construction box for not implemented features
        st.markdown(f"""
        <div style="
            background-color: #fef3c7; 
            border: 3px dashed #d97706; 
            padding: 15px; 
            border-radius: 8px; 
            margin: 10px 0;
            color: #92400e;
            font-weight: bold;
        ">
            FEATURE NOT IMPLEMENTED<br>
            <span style="font-size: 0.9em;">This tab is a placeholder showing the planned interface.</span><br>
            <span style="font-size: 0.8em; font-weight: normal;">
                <strong>Planned Source:</strong> {source_info['target_source']}<br>
                <strong>Implementation:</strong> {source_info['note']}
            </span>
        </div>
        """, unsafe_allow_html=True)

def render_dashboard_disclaimer() -> None:
    """
    Render a global dashboard disclaimer about data sources.
    Call this at the bottom of the main app.
    """
    st.markdown("---")
    st.markdown("""
    ### Dashboard Status
    
    This energy dashboard is under active development with mixed data sources:
    
    - **Live Data**: Real-time integration with automated updates
    - **Demo Data**: Sample data for development and testing  
    - **Not Implemented**: Planned features with empty schemas
    
    **Development Goal**: Migrate all data sources to live, automated feeds for a comprehensive 
    view of the Texas electricity market.
    """)
    
    # Summary table
    st.markdown("#### Current Implementation Status")
    
    status_data = []
    for dataset, info in DATA_SOURCES.items():
        status_label = {
            'live': 'Live',
            'demo': 'Demo', 
            'stub': 'Stub'
        }.get(info['status'], 'Unknown')
        
        dataset_name = {
            'fuelmix': 'ERCOT Fuel Mix',
            'price_map': 'Price Map',
            'generation': 'Generation Map', 
            'queue': 'Interconnection Queue'
        }.get(dataset, dataset)
        
        status_data.append({
            'Feature': dataset_name,
            'Status': status_label,
            'Source': info.get('source', 'Unknown')
        })
    
    df_status = st.dataframe(status_data, hide_index=True)
    
    st.markdown("""
    <div style="text-align: center; font-size: 0.9em; color: #6b7280; margin-top: 1rem;">
        <strong>Texas Association of Business Energy Dashboard</strong> • 
        Built with Streamlit • Data via EIA API • 
        <a href="https://github.com/Charlie9170/TABEnergyDashboard" target="_blank" style="color: #16a34a;">View Source</a>
    </div>
    """, unsafe_allow_html=True)