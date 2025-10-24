"""
Interconnection Queue Tab - ERCOT Planned Generation Projects

Clean, minimal implementation focusing on core functionality.
"""

import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.graph_objects as go
import plotly.express as px
import numpy as np

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from utils.loaders import load_parquet, get_last_updated
from utils.data_sources import render_data_source_footer
from utils.colors import get_fuel_color_rgba, FUEL_COLORS_HEX


def render():
    """Render the Interconnection Queue tab with clean, minimal approach."""
    
    # Clean header with consistent styling
    st.header("ERCOT Interconnection Queue")
    st.markdown("Real projects from ERCOT's Capacity, Demand and Reserves (CDR) Report showing the interconnection queue pipeline of future generation capacity.")
    
    # Load data using the correct function signature
    try:
        queue_df = load_parquet('queue.parquet', 'queue')
        last_update = get_last_updated(queue_df)
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return
    
    if queue_df.empty:
        st.warning("No queue data available.")
        return
    
    # Simple status indicator with success styling
    st.success(f"📊 Loaded {len(queue_df)} projects from ERCOT CDR | Updated: {last_update}")
    
    # Clean and prepare data
    df = queue_df.copy()
    
    # Professional metrics using native Streamlit
    col1, col2, col3 = st.columns(3)
    
    # Determine capacity column (schema uses 'proposed_mw')
    capacity_col = 'proposed_mw' if 'proposed_mw' in df.columns else ('capacity_mw' if 'capacity_mw' in df.columns else None)
    if capacity_col is None:
        st.error("Queue data missing capacity column ('proposed_mw' or 'capacity_mw').")
        st.info(f"Available columns: {list(df.columns)}")
        return

    with col1:
        total_capacity = df[capacity_col].sum()
        st.metric(
            label="Total Planned Capacity",
            value=f"{total_capacity:,.0f} MW",
            help="Combined capacity of all projects in the interconnection queue"
        )
    
    with col2:
        project_count = len(df)
        st.metric(
            label="Projects in Queue", 
            value=f"{project_count:,}",
            help="Number of generation projects awaiting interconnection"
        )
    
    with col3:
        fuel_types = df['fuel'].nunique()
        st.metric(
            label="Fuel Types",
            value=fuel_types,
            help="Diversity of generation technologies in the queue"
        )
    
    # Simple map section
    st.subheader("🗺️ Project Locations")
    
    # Add colors for visualization
    df['color'] = [get_fuel_color_rgba(f, alpha=180) for f in df['fuel']]
    df['radius'] = np.clip(df[capacity_col] * 15, 80, 1500)
    
    # Create map
    view_state = pdk.ViewState(
        latitude=df['lat'].mean(),
        longitude=df['lon'].mean(),
        zoom=5.5,
        pitch=0,
    )
    
    layer = pdk.Layer(
        'ScatterplotLayer',
        data=df,
        get_position='[lon, lat]',
        get_color='color',
        get_radius='radius',
        pickable=True,
        opacity=0.7
    )
    
    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_style='mapbox://styles/mapbox/light-v10'
    )
    
    st.pydeck_chart(deck, use_container_width=True)
    
    # Simple fuel breakdown
    st.subheader("⚡ Capacity by Fuel Type")
    
    fuel_capacity = df.groupby('fuel')[capacity_col].sum().sort_values(ascending=False)
    
    # Simple bar chart
    fig = go.Figure(data=[
        go.Bar(
            x=fuel_capacity.index,
            y=fuel_capacity.values,
            marker_color=[FUEL_COLORS_HEX.get(fuel.replace(' ', '').upper(), '#64748b') for fuel in fuel_capacity.index]
        )
    ])
    
    fig.update_layout(
        title="Planned Capacity by Fuel Type",
        xaxis_title="Fuel Type",
        yaxis_title="Capacity (MW)",
        template="plotly_white",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Simple data table
    st.subheader("📋 Project Summary")
    
    # Show key columns only
    cols = ['project_name', 'fuel', capacity_col, 'status']
    display_df = df[cols].copy()
    # Rename for presentation
    pretty_cols = ['Project Name', 'Fuel Type', 'Capacity (MW)', 'Status']
    display_df.columns = pretty_cols
    
    st.dataframe(
        display_df, 
        use_container_width=True,
        hide_index=True
    )
    
    # Simple footer
    render_data_source_footer('queue', last_update)