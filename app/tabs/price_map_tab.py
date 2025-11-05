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
from utils.export import create_download_button


def render():
    """Render the Price Map tab with comprehensive error handling."""
    
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
        <h3 style="margin-top: 0; color: #dc2626;">DEMO DATA ONLY</h3>
        <p style="font-size: 1.1em; margin-bottom: 10px;">
            This map shows <strong>sample data for development purposes</strong>
        </p>
        <p style="font-size: 0.9em; margin-bottom: 0; opacity: 0.8;">
            Will be replaced with real ERCOT price data when implemented
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Header - ultra compact
    st.markdown("### ERCOT Price Map")
    st.markdown(
        "Real-time locational marginal prices (LMP) across ERCOT nodes. "
        "Dot size indicates price level; larger dots represent higher prices."
    )
    
    try:
        # Load data with error handling
        df = load_parquet("price_map.parquet", "price_map", allow_empty=True)
        
        # Check if data is empty
        if df is None or len(df) == 0:
            st.warning("⚠️ **No price data available**")
            st.info("Run the ETL script to generate demo price map data.")
            st.code("python etl/price_map_etl.py", language="bash")
            return
        
        # Calculate price quantiles for color coding
        df['price_quantile'] = pd.qcut(
            df['price_cperkwh'],
            q=5,
            labels=['Very Low', 'Low', 'Medium', 'High', 'Very High'],
            duplicates='drop'
        ).astype(str)  # Convert categorical to string to avoid hashing issues
        
        # Map quantiles to colors (red/coral scale matching generation map)
        quantile_colors = {
            'Very Low': [255, 150, 130, 180],   # Light coral
            'Low': [255, 120, 100, 180],        # Coral
            'Medium': [255, 90, 70, 180],       # Red-coral
            'High': [230, 60, 50, 180],         # Deep red
            'Very High': [200, 30, 30, 180],    # Dark red
        }
        
        # Assign colors using list comprehension to avoid pandas indexing issues
        df['color'] = [quantile_colors[q] for q in df['price_quantile']]
        
        # Calculate radius based on price (scale to 100-1000 meters)
        min_price = df['price_cperkwh'].min()
        max_price = df['price_cperkwh'].max()
        price_range = max_price - min_price if max_price > min_price else 1
        df['radius'] = 100 + ((df['price_cperkwh'] - min_price) / price_range) * 900
        
        # Unified metric cards matching other tabs
        col1, col2, col3 = st.columns(3)
        
        with col1:
            avg_price = df['price_cperkwh'].mean()
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-card-title">Average Price/kWh</div>
                <div class="metric-card-value">{avg_price:.2f}¢</div>
                <div class="metric-card-subtitle">ERCOT Grid Average</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            min_price_val = df['price_cperkwh'].min()
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-card-title">Minimum Price/kWh</div>
                <div class="metric-card-value">{min_price_val:.2f}¢</div>
                <div class="metric-card-subtitle">Lowest Node Price</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            max_price_val = df['price_cperkwh'].max()
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-card-title">Maximum Price/kWh</div>
                <div class="metric-card-value">{max_price_val:.2f}¢</div>
                <div class="metric-card-subtitle">Highest Node Price</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("")  # Spacing
        
        # Calculate map center from data
        center_lat = df['lat'].mean()
        center_lon = df['lon'].mean()
        
        # Texas-focused locked viewport - MAXIMUM ZOOM OUT (4.7 - NEW VALUE!)
        view_state = pdk.ViewState(
            latitude=31.0,
            longitude=-99.5,
            zoom=4.7,
            pitch=0,
            min_zoom=4.7,
            max_zoom=4.7,
        )
        
        # Tooltip configuration matching generation map
        tooltip = {
            "html": "<b>{region}</b><br/>Price: {price_cperkwh}¢/kWh<br/>Level: {price_quantile}",
            "style": {
                "backgroundColor": "white",
                "color": "black",
                "fontSize": "14px",
                "borderRadius": "6px",
                "padding": "8px 12px",
                "boxShadow": "0 2px 8px rgba(0,0,0,0.15)"
            }
        }
        
        # Create pydeck layer with white outlines like generation map
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
            auto_highlight=True,
            stroked=True,
            filled=True,
            get_line_color=[255, 255, 255, 150],  # White outline like generation map
            line_width_min_pixels=1,
            line_width_max_pixels=2,
            opacity=0.8
        )
        
        # Render map with LIGHT background matching generation map
        deck = pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            map_style='mapbox://styles/mapbox/light-v10',  # Changed from dark to light
            tooltip=tooltip,  # type: ignore
            views=[pdk.View(type='MapView', controller=False)]
        )
        
        st.pydeck_chart(deck, height=500, use_container_width=True)
        
        # Data Export Section
        st.markdown("---")
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("**Download Price Data** (Demo Data - Real data coming with YesEnergy)")
        with col2:
            create_download_button(
                df=df,
                filename_prefix="price_map_demo",
                label="Download Price Data"
            )
        
        # Legend (red/coral color scheme matching generation map)
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
        st.code("python etl/price_map_etl.py", language="bash")
        
    except pd.errors.ParserError:
        st.error(f"❌ **File Corrupted**: Unable to read price map data")
        st.info("🔄 The parquet file may be damaged. Re-run the ETL script.")
        st.code("python etl/price_map_etl.py", language="bash")
        
    except Exception as e:
        st.error(f"❌ **Unexpected error loading price map**: {str(e)}")
        st.info("🔄 Try refreshing the page. If the issue persists, re-run the ETL script.")
        st.code("python etl/price_map_etl.py", language="bash")
