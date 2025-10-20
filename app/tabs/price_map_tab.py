"""
Price Map Tab - ERCOT Node Price Visualization

Displays electricity prices across ERCOT nodes:
- Interactive map with dot size proportional to price
- Color-coded by price quantiles
- Geographic distribution of electricity costs
"""

import streamlit as st
import pandas as pd
import pydeck as pdk

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from utils.loaders import load_parquet, get_last_updated
from utils.data_sources import render_data_source_footer


def render():
    """Render the Price Map tab."""
    
    # Temporary demo data warning
    st.markdown("""
    <div style="
        background-color: #fef2f2; 
        border: 3px dashed #dc2626; 
        padding: 20px; 
        border-radius: 10px; 
        margin: 20px 0;
        text-align: center;
        color: #991b1b;
    ">
        <h3 style="margin-top: 0; color: #dc2626;">⚠️ DEMO DATA ONLY ⚠️</h3>
        <p style="font-size: 1.1em; margin-bottom: 10px;">
            This map shows <strong>sample data for development purposes</strong>
        </p>
        <p style="font-size: 0.9em; margin-bottom: 0; opacity: 0.8;">
            Will be replaced with real ERCOT price data when implemented
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Header
    st.header("ERCOT Price Map")
    st.markdown(
        "Real-time locational marginal prices (LMP) across ERCOT nodes. "
        "Dot size indicates price level; larger dots represent higher prices."
    )
    
    try:
        # Load data
        df = load_parquet("price_map.parquet", "price_map")
        
        # Calculate price quantiles for color coding
        df['price_quantile'] = pd.qcut(
            df['price_cperkwh'],
            q=5,
            labels=['Very Low', 'Low', 'Medium', 'High', 'Very High'],
            duplicates='drop'
        ).astype(str)  # Convert categorical to string to avoid hashing issues
        
        # Map quantiles to colors (green to red scale)
        quantile_colors = {
            'Very Low': [20, 184, 166, 200],   # Teal
            'Low': [52, 211, 153, 200],        # Green
            'Medium': [234, 179, 8, 200],      # Yellow
            'High': [251, 146, 60, 200],       # Orange
            'Very High': [239, 68, 68, 200],   # Red
        }
        
        # Assign colors using list comprehension to avoid pandas indexing issues
        df['color'] = [quantile_colors[q] for q in df['price_quantile']]
        
        # Calculate radius based on price (scale to 100-1000 meters)
        min_price = df['price_cperkwh'].min()
        max_price = df['price_cperkwh'].max()
        price_range = max_price - min_price if max_price > min_price else 1
        df['radius'] = 100 + ((df['price_cperkwh'] - min_price) / price_range) * 900
        
        # Summary stats
        col1, col2, col3 = st.columns(3)
        
        with col1:
            avg_price = df['price_cperkwh'].mean()
            st.markdown(f"""
            <div class="kpi-card">
                <p class="kpi-value">{avg_price:.2f}¢</p>
                <p class="kpi-label">Average Price/kWh</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            min_price_val = df['price_cperkwh'].min()
            st.markdown(f"""
            <div class="kpi-card">
                <p class="kpi-value">{min_price_val:.2f}¢</p>
                <p class="kpi-label">Minimum Price/kWh</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            max_price_val = df['price_cperkwh'].max()
            st.markdown(f"""
            <div class="kpi-card">
                <p class="kpi-value">{max_price_val:.2f}¢</p>
                <p class="kpi-label">Maximum Price/kWh</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("")  # Spacing
        
        # Calculate map center from data
        center_lat = df['lat'].mean()
        center_lon = df['lon'].mean()
        
        # Define view state for Texas
        view_state = pdk.ViewState(
            latitude=center_lat,
            longitude=center_lon,
            zoom=6,
            pitch=0,
        )
        
        # Create pydeck layer  
        layer = pdk.Layer(
            "ScatterplotLayer",
            data=df,
            get_position=['lon', 'lat'],
            get_color='color',
            get_radius='radius',
            radius_scale=1,
            radius_min_pixels=8,
            radius_max_pixels=100,
            pickable=True,
            stroked=True,
            filled=True,
            line_width_min_pixels=1,
        )
        
        # Render map (remove problematic tooltip for now)
        deck = pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            map_style='mapbox://styles/mapbox/dark-v10',
        )
        
        st.pydeck_chart(deck)
        
        # Legend
        st.markdown("### Price Levels")
        legend_cols = st.columns(5)
        legend_items = [
            ('Very Low', '#14b8a6'),
            ('Low', '#34d399'),
            ('Medium', '#eab308'),
            ('High', '#fb923c'),
            ('Very High', '#ef4444'),
        ]
        
        for col, (label, color) in zip(legend_cols, legend_items):
            col.markdown(
                f'<div style="display: inline-block; width: 16px; height: 16px; '
                f'background-color: {color}; border-radius: 50%; margin-right: 8px;"></div> {label}',
                unsafe_allow_html=True
            )
        
        # Data source footer
        last_updated = get_last_updated(df)
        render_data_source_footer('price_map', last_updated)
        
    except Exception as e:
        st.error(f"Error loading price map data: {str(e)}")
        st.info("Please ensure the ETL script has been run to generate the data file.")
