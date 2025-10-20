"""
Generation Map Tab - Texas Power Generation Facilities

Displays existing power generation facilities across Texas:
- Interactive map colored by fuel type
- Dot size proportional to generation capacity
- Distribution of generation infrastructure
"""

import streamlit as st
import pandas as pd
import pydeck as pdk

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from utils.loaders import load_parquet, get_last_updated
from utils.colors import get_fuel_color_rgba, FUEL_COLORS_HEX


def render():
    """Render the Generation Map tab."""
    
    # Header
    st.header("Texas Power Generation Map")
    st.markdown(
        "Existing power generation facilities across Texas. "
        "Facilities are color-coded by fuel type, with size indicating capacity."
    )
    
    try:
        # Load data
        df = load_parquet("generation.parquet", "generation")
        
        # Add color column based on fuel type
        df['color'] = df['fuel'].apply(lambda f: get_fuel_color_rgba(f, alpha=200))
        
        # Scale radius by capacity (50m per MW, capped at 2000m)
        df['radius'] = df['capacity_mw'].apply(lambda x: min(x * 50, 2000))
        
        # Summary stats
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_capacity = df['capacity_mw'].sum()
            st.markdown(f"""
            <div class="kpi-card">
                <p class="kpi-value">{total_capacity:,.0f} MW</p>
                <p class="kpi-label">Total Generation Capacity</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            plant_count = len(df)
            st.markdown(f"""
            <div class="kpi-card">
                <p class="kpi-value">{plant_count:,}</p>
                <p class="kpi-label">Power Plants</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            fuel_types = df['fuel'].nunique()
            st.markdown(f"""
            <div class="kpi-card">
                <p class="kpi-value">{fuel_types}</p>
                <p class="kpi-label">Fuel Types</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("")  # Spacing
        
        # Create pydeck map
        view_state = pdk.ViewState(
            latitude=df['lat'].mean() if len(df) > 0 else 31.0,
            longitude=df['lon'].mean() if len(df) > 0 else -99.0,
            zoom=5.5,
            pitch=0,
        )
        
        # ScatterplotLayer for generation facilities
        layer = pdk.Layer(
            'ScatterplotLayer',
            data=df,
            get_position='[lon, lat]',
            get_color='color',
            get_radius='radius',
            pickable=True,
            opacity=0.6,
            stroked=True,
            filled=True,
            line_width_min_pixels=1,
        )
        
        # Tooltip configuration
        tooltip = {
            "html": """
            <b>{plant_name}</b><br/>
            <b>Fuel:</b> {fuel}<br/>
            <b>Capacity:</b> {capacity_mw:.1f} MW
            """,
            "style": {
                "backgroundColor": "#1f2937",
                "color": "#e5e7eb",
                "border": "1px solid #374151",
                "borderRadius": "4px",
                "padding": "8px"
            }
        }
        
        # Render map
        deck = pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            tooltip=tooltip,
            map_style='mapbox://styles/mapbox/dark-v10',
        )
        
        st.pydeck_chart(deck)
        
        # Fuel type breakdown
        st.markdown("### Capacity by Fuel Type")
        fuel_capacity = df.groupby('fuel')['capacity_mw'].sum().sort_values(ascending=False)
        
        # Create columns for legend
        num_fuels = len(fuel_capacity)
        cols_per_row = 4
        rows = (num_fuels + cols_per_row - 1) // cols_per_row
        
        for i in range(rows):
            cols = st.columns(cols_per_row)
            for j in range(cols_per_row):
                idx = i * cols_per_row + j
                if idx < num_fuels:
                    fuel = fuel_capacity.index[idx]
                    capacity = fuel_capacity.iloc[idx]
                    color = FUEL_COLORS_HEX.get(fuel.upper(), '#64748b')
                    cols[j].markdown(
                        f'<div style="display: inline-block; width: 16px; height: 16px; '
                        f'background-color: {color}; border-radius: 50%; margin-right: 8px;"></div> '
                        f'<b>{fuel}:</b> {capacity:,.0f} MW',
                        unsafe_allow_html=True
                    )
        
        # Footer
        last_updated = get_last_updated(df)
        st.markdown(f"""
        <div class="footer">
            <strong>Source:</strong> U.S. Energy Information Administration (EIA) • 
            <strong>Last Updated:</strong> {last_updated}
        </div>
        """, unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"Error loading generation data: {str(e)}")
        st.info("Please ensure the ETL script has been run to generate the data file.")
