"""Texas Association of Business Energy Dashboard - Main Application."""

import streamlit as st
from Tabs import (
    render_fuel_mix_tab,
    render_price_map_tab,
    render_generation_map_tab,
    render_ercot_queue_tab
)

# Page configuration
st.set_page_config(
    page_title="TAB Energy Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Main title
st.title("Texas Association of Business Energy Dashboard")
st.markdown("Automated ERCOT & EIA data visualization dashboard")

# Sidebar navigation
with st.sidebar:
    st.header("Navigation")
    tab_selection = st.radio(
        "Select Dashboard",
        [
            "ERCOT Fuel Mix",
            "ERCOT Price Map",
            "TX Generation Map",
            "ERCOT Queue"
        ]
    )
    
    st.markdown("---")
    st.markdown("### About")
    st.markdown(
        "This dashboard provides real-time insights into Texas electricity markets, "
        "generation resources, and interconnection projects."
    )
    
    st.markdown("---")
    st.markdown("### Data Sources")
    st.markdown("- EIA API v2 (ERCO region)")
    st.markdown("- ERCOT Public Data")
    
    st.markdown("---")
    st.caption("Texas Association of Business")

# Render selected tab
if tab_selection == "ERCOT Fuel Mix":
    render_fuel_mix_tab()
elif tab_selection == "ERCOT Price Map":
    render_price_map_tab()
elif tab_selection == "TX Generation Map":
    render_generation_map_tab()
elif tab_selection == "ERCOT Queue":
    render_ercot_queue_tab()
