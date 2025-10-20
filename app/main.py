"""
Texas Association of Business Energy Dashboard

A Streamlit application for visualizing ERCOT energy data including:
- Real-time fuel mix from EIA
- Price maps across ERCOT nodes
- Power generation facilities
- Interconnection queue projects

Data is automatically updated via GitHub Actions.
"""

import streamlit as st

# Import tab modules
from tabs import fuelmix_tab, price_map_tab, generation_tab, queue_tab
from utils.data_sources import render_dashboard_disclaimer

# Page configuration
st.set_page_config(
    page_title="TAB Energy Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for spacing and polish
st.markdown("""
<style>
    /* Reduce padding at top of page */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Style for KPI cards */
    .kpi-card {
        background-color: #1f2937;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border: 1px solid #374151;
        margin: 0.5rem 0;
    }
    
    .kpi-value {
        font-size: 2rem;
        font-weight: bold;
        color: #16a34a;
        margin: 0;
    }
    
    .kpi-label {
        font-size: 0.875rem;
        color: #9ca3af;
        margin: 0;
    }
    
    /* Footer styling */
    .footer {
        margin-top: 3rem;
        padding-top: 1rem;
        border-top: 1px solid #374151;
        color: #9ca3af;
        font-size: 0.875rem;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.title("Texas Association of Business Energy Dashboard")
st.markdown("Real-time visualization of ERCOT electricity data and infrastructure")

# Sidebar navigation
st.sidebar.title("Navigation")
st.sidebar.markdown("Select a view to explore different aspects of the Texas energy landscape.")

# Tab selection
tab_selection = st.sidebar.radio(
    "Select Dashboard View:",
    ["Fuel Mix", "Price Map", "Generation Map", "Interconnection Queue"],
    label_visibility="collapsed"
)

# Render selected tab
if tab_selection == "Fuel Mix":
    fuelmix_tab.render()
elif tab_selection == "Price Map":
    price_map_tab.render()
elif tab_selection == "Generation Map":
    generation_tab.render()
elif tab_selection == "Interconnection Queue":
    queue_tab.render()

# Global dashboard disclaimer and status
render_dashboard_disclaimer()

# Footer with info
st.sidebar.markdown("---")
st.sidebar.markdown("""
### About
This dashboard provides automated insights into Texas electricity markets and infrastructure.

**Data Sources:**
- EIA (U.S. Energy Information Administration)
- ERCOT (Electric Reliability Council of Texas)

**Updates:** Every 6 hours via GitHub Actions
""")
