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
        'status': 'live',
        'source': 'U.S. Energy Information Administration (EIA)',
        'dataset': 'RTO fuel-type data (ERCOT)',
        'api': 'EIA v2 electricity/rto/fuel-type-data',
        'respondent': 'ERCO (ERCOT)',
        'coverage': 'Hourly ERCOT generation by fuel type (rolling 7 days)',
        'update_frequency': 'Dashboard ETL every 6 hours',
        'url': 'https://www.eia.gov/opendata/',
    },
    'price_map': {
        'status': 'live',
        'source': 'Electric Reliability Council of Texas (ERCOT)',
        'dataset': 'Real-Time Settlement Point Prices',
        'api': 'Real-Time Settlement Point Prices (SPP)',
        'coverage': '15 settlement points (9 major hubs + 6 strategic nodes)',
        'update_frequency': 'Source updates about every 5 minutes; dashboard ETL every 6 hours',
        'url': 'https://www.ercot.com/mp/data-products/data-product-details?id=NP6-785-ER',
    },
    'generation': {
        'status': 'live',
        'source': 'U.S. Energy Information Administration (EIA)',
        'dataset': 'Operating generator capacity and EIA-923 facility-fuel',
        'api': 'EIA v2 operating-generator-capacity + facility-fuel',
        'coverage': 'Texas plants ≥1 MW with measured EIA-923 generation',
        'update_frequency': 'Dashboard ETL every 6 hours; EIA publications are periodic',
        'url': 'https://www.eia.gov/opendata/',
    },
    'queue': {
        'status': 'live',
        'source': 'Electric Reliability Council of Texas (ERCOT)',
        'dataset': 'Generator Interconnection Status (GIS) Report',
        'api': 'ERCOT Generator Interconnection Status (GIS) Report',
        'coverage': 'Public Large Gen and Small Gen detail sheets',
        'update_frequency': 'ERCOT republishes monthly; dashboard ETL checks every 6 hours',
        'url': 'https://www.ercot.com/mp/data-products/data-product-details?id=PG7-200-ER',
    },
    'minerals': {
        'status': 'live',
        'source': 'Compiled from public geological surveys and industry disclosures',
        'dataset': 'Texas mineral deposits (manually curated)',
        'api': 'Texas General Land Office, USGS, industry disclosures',
        'coverage': 'Selected REE and critical-mineral deposits in Texas',
        'update_frequency': 'Manual; not an automated feed',
        'url': 'https://www.glo.texas.gov/',
        'public_note': 'Not comparable in freshness or completeness to EIA or ERCOT automated feeds.',
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

def render_freshness_banner(label: str, timestamp: str) -> None:
    """Prominent last-updated indicator (pre-cleanup green status box)."""
    st.success(f"**{label}** — Last Updated: {timestamp}")


def render_data_source_footer(
    dataset: str,
    last_updated: Optional[str] = None,
    *,
    data_through: Optional[str] = None,
) -> None:
    """
    Compact source / freshness line for the bottom of a data tab.

    Distinguishes the underlying source period (`data_through`) from the
    dashboard ETL write time (`last_updated`).
    """
    if dataset not in DATA_SOURCES:
        st.error(f"Unknown dataset: {dataset}")
        return

    source_info = DATA_SOURCES[dataset]
    status = source_info['status']

    st.markdown("---")

    if status == 'live':
        dataset_label = source_info.get('dataset') or source_info.get('api', '')
        lines = [f"Source: {source_info['source']} · {dataset_label}"]
        if data_through:
            lines.append(f"Data through: {data_through}")
        if last_updated:
            lines.append(f"Dashboard refreshed: {last_updated}")
        note = source_info.get('public_note')
        if note:
            lines.append(note)
        st.caption("  \n".join(lines))

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