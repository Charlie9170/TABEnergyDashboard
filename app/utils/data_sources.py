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
        'status': 'demo',
        'source': 'Demo Data (Development Only)',
        'api': 'Static sample data with Texas coordinates',
        'note': 'Replace with ERCOT CDR real-time LMP data',
        'target_source': 'ERCOT Contour Data Records (CDR)',
        'target_url': 'https://www.ercot.com/content/cdr/contours/rtmLmp.html',
    },
    'generation': {
        'status': 'stub',
        'source': 'Empty Schema (Not Implemented)',
        'note': 'Placeholder for EIA Power Plants data',
        'target_source': 'EIA Atlas Power Plants Feature Service',
        'target_url': 'https://atlas.eia.gov/datasets/eia::power-plants/',
    },
    'queue': {
        'status': 'stub',
        'source': 'Empty Schema (Not Implemented)', 
        'note': 'Placeholder for ERCOT interconnection queue data',
        'target_source': 'ERCOT Public Reports or interconnection.fyi',
        'target_url': 'https://www.interconnection.fyi/?market=ERCOT',
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
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if status == 'live':
            st.markdown(f"""
            **📊 Data Source:** {source_info['source']}  
            **🔌 API:** {source_info['api']}  
            **🔄 Updates:** {source_info['update_frequency']}  
            {f"**⏰ Last Updated:** {last_updated}" if last_updated else ""}
            """)
            
        elif status == 'demo':
            st.markdown(f"""
            **⚠️ {get_data_status_badge(dataset)}** - This tab shows demonstration data for development purposes.  
            **🎯 Target Source:** {source_info['target_source']}  
            **📝 Note:** {source_info['note']}
            """)
            
        elif status == 'stub':
            st.markdown(f"""
            **🚧 {get_data_status_badge(dataset)}** - This feature is planned but not yet implemented.  
            **🎯 Planned Source:** {source_info['target_source']}  
            **📝 Implementation:** {source_info['note']}
            """)
    
    with col2:
        st.markdown(f"""
        <div style="text-align: right; font-size: 0.8em; color: #9ca3af;">
            {get_data_status_badge(dataset)}
        </div>
        """, unsafe_allow_html=True)

def render_dashboard_disclaimer() -> None:
    """
    Render a global dashboard disclaimer about data sources.
    Call this at the bottom of the main app.
    """
    st.markdown("---")
    st.markdown("""
    ### 📋 Dashboard Status
    
    This energy dashboard is under active development with mixed data sources:
    
    - 🟢 **Live Data**: Real-time integration with automated updates
    - 🟡 **Demo Data**: Sample data for development and testing  
    - 🔴 **Not Implemented**: Planned features with empty schemas
    
    **Development Goal**: Migrate all data sources to live, automated feeds for a comprehensive 
    view of the Texas electricity market.
    """)
    
    # Summary table
    st.markdown("#### Current Implementation Status")
    
    status_data = []
    for dataset, info in DATA_SOURCES.items():
        status_emoji = {
            'live': '🟢 Live',
            'demo': '🟡 Demo', 
            'stub': '🔴 Stub'
        }.get(info['status'], '❓ Unknown')
        
        dataset_name = {
            'fuelmix': 'ERCOT Fuel Mix',
            'price_map': 'Price Map',
            'generation': 'Generation Map', 
            'queue': 'Interconnection Queue'
        }.get(dataset, dataset)
        
        status_data.append({
            'Feature': dataset_name,
            'Status': status_emoji,
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