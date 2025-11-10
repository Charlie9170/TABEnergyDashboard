"""
Price Map Tab - ERCOT Real-Time LMP Visualization

Displays real-time electricity prices across ERCOT weather zones:
- Live data from ERCOT Public API (updates every 5 minutes)
- Interactive map with prices by geographic zone
- Color-coded by price levels (green=low, red=high)
- Auto-updates every 15 minutes via GitHub Actions
"""

import streamlit as st
import pandas as pd
import pydeck as pdk
from datetime import datetime

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from utils.loaders import load_parquet, get_last_updated
from utils.data_sources import render_data_source_footer
from utils.export import create_download_button


def render():
    """Render the Price Map tab with real-time ERCOT LMP data."""
    
    # Header - ultra compact
    st.markdown("### ERCOT Real-Time Price Map")
    
    try:
        # Load data with error handling
        df = load_parquet("price_map.parquet", "price_map", allow_empty=True)
        
        # Check if data is empty
        if df is None or len(df) == 0:
            st.warning("⚠️ **No price data available**")
            st.info("Run the ETL script to fetch real-time ERCOT LMP data.")
            st.code("python etl/ercot_lmp_etl.py", language="bash")
            return
        
        # Use avg_price column (from ERCOT aggregation)
        price_col = 'avg_price' if 'avg_price' in df.columns else 'price_cperkwh'
        
        # Calculate price quantiles for color coding
        df['price_quantile'] = pd.qcut(
            df[price_col],
            q=5,
            labels=['Very Low', 'Low', 'Medium', 'High', 'Very High'],
            duplicates='drop'
        ).astype(str)
        
        # Map quantiles to colors (red/coral scale matching generation map)
        quantile_colors = {
            'Very Low': [255, 150, 130, 180],   # Light coral
            'Low': [255, 120, 100, 180],        # Coral
            'Medium': [255, 90, 70, 180],       # Red-coral
            'High': [230, 60, 50, 180],         # Deep red
            'Very High': [200, 30, 30, 180],    # Dark red
        }
        
        # Assign colors using list comprehension
        df['color'] = [quantile_colors[q] for q in df['price_quantile']]
        
        # Calculate radius based on price (scale to 8-30k for zone visibility)
        min_price = df[price_col].min()
        max_price = df[price_col].max()
        price_range = max_price - min_price if max_price > min_price else 1
        df['radius'] = 8000 + ((df[price_col] - min_price) / price_range) * 22000
        
        # Unified metric cards matching other tabs
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            avg_price = df[price_col].mean()
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-card-title">Average LMP</div>
                <div class="metric-card-value">${avg_price:.2f}/MWh</div>
                <div class="metric-card-subtitle">ERCOT Grid Average</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            min_price_val = df[price_col].min()
            min_zone = df.loc[df[price_col].idxmin(), 'zone'] if 'zone' in df.columns else 'N/A'
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-card-title">Lowest Price</div>
                <div class="metric-card-value">${min_price_val:.2f}/MWh</div>
                <div class="metric-card-subtitle">{min_zone}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            max_price_val = df[price_col].max()
            max_zone = df.loc[df[price_col].idxmax(), 'zone'] if 'zone' in df.columns else 'N/A'
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-card-title">Highest Price</div>
                <div class="metric-card-value">${max_price_val:.2f}/MWh</div>
                <div class="metric-card-subtitle">{max_zone}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            price_spread = max_price_val - min_price_val
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-card-title">Price Spread</div>
                <div class="metric-card-value">${price_spread:.2f}/MWh</div>
                <div class="metric-card-subtitle">Max - Min Difference</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("")  # Spacing
        
        # Real-time data indicator - placed below metrics
        if 'last_updated' in df.columns:
            last_update = pd.to_datetime(df['last_updated'].iloc[0])
            minutes_ago = (datetime.now() - last_update).total_seconds() / 60
            st.success(f"**Live Data**: ERCOT Real-Time LMP - Updated {minutes_ago:.0f} minutes ago")
        
        st.markdown("---")
        
        # Texas-focused locked viewport
        view_state = pdk.ViewState(
            latitude=31.0,
            longitude=-99.5,
            zoom=4.7,
            pitch=0,
            min_zoom=4.7,
            max_zoom=4.7,
        )
        
        # Tooltip configuration for zone-level data
        if 'zone' in df.columns:
            tooltip_html = "<b>{zone}</b><br/>Avg: ${avg_price:.2f}/MWh"
            if 'min_price' in df.columns:
                tooltip_html += "<br/>Min: ${min_price:.2f} | Max: ${max_price:.2f}"
            tooltip_html += "<br/>Level: {price_quantile}"
        else:
            tooltip_html = "<b>Zone Price</b><br/>Price: ${" + price_col + ":.2f}/MWh<br/>Level: {price_quantile}"
        
        tooltip = {
            "html": tooltip_html,
            "style": {
                "backgroundColor": "white",
                "color": "black",
                "fontSize": "14px",
                "borderRadius": "6px",
                "padding": "8px 12px",
                "boxShadow": "0 2px 8px rgba(0,0,0,0.15)"
            }
        }
        
        # Create pydeck layer with white outlines
        layer = pdk.Layer(
            "ScatterplotLayer",
            data=df,
            get_position=['lon', 'lat'],
            get_color='color',
            get_radius='radius',
            radius_scale=1,
            radius_min_pixels=15,
            radius_max_pixels=50,
            pickable=True,
            auto_highlight=True,
            stroked=True,
            filled=True,
            get_line_color=[255, 255, 255, 150],
            line_width_min_pixels=2,
            line_width_max_pixels=3,
            opacity=0.8
        )
        
        # Render map with LIGHT background
        deck = pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            map_style='mapbox://styles/mapbox/light-v10',
            tooltip=tooltip,  # type: ignore
            views=[pdk.View(type='MapView', controller=False)]
        )
        
        st.pydeck_chart(deck, height=500, use_container_width=True)
        
        # Data Export Section
        st.markdown("---")
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("**Download Real-Time LMP Data** (ERCOT Zone Aggregates)")
        with col2:
            create_download_button(
                df=df,
                filename_prefix="ercot_lmp_realtime",
                label="Download LMP Data"
            )
        
        # Legend (red/coral color scheme)
        st.markdown("### Price Levels")
        legend_cols = st.columns(5)
        legend_items = [
            ('Very Low', '#ff9682'),
            ('Low', '#ff7864'),
            ('Medium', '#ff5a46'),
            ('High', '#e63c32'),
            ('Very High', '#c81e1e'),
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
        
    except KeyError as e:
        st.error(f"❌ **Data Format Error**: Missing required column: {str(e)}")
        st.info("🔄 The data file may be corrupted. Try re-running the ETL script.")
        st.code("python etl/ercot_lmp_etl.py", language="bash")
        
    except pd.errors.ParserError:
        st.error(f"❌ **File Corrupted**: Unable to read price map data")
        st.info("🔄 The parquet file may be damaged. Re-run the ETL script.")
        st.code("python etl/ercot_lmp_etl.py", language="bash")
        
    except Exception as e:
        st.error(f"❌ **Unexpected error loading price map**: {str(e)}")
        st.info("🔄 Try refreshing the page. If the issue persists, re-run the ETL script.")
        st.code("python etl/price_map_etl.py", language="bash")
