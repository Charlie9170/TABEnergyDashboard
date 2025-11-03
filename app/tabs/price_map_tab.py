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

# Add parent directory to path for local imports
sys.path.append(str(Path(__file__).parent.parent))  # noqa: E402

from utils.loaders import load_parquet, get_last_updated  # noqa: E402
from utils.data_sources import render_data_source_footer  # noqa: E402


def render():
    """Render the Price Map tab."""

    # Temporary demo data warning
    st.markdown("""
    <div style="
        background-color: #fef2f2;
        border: 3px dashed #dc2626;
        color: #dc2626;
        padding: 1em;
        margin-bottom: 1.5em;
        border-radius: 8px; ">
        <b>Demo Data:</b> This map uses sample data for demonstration only.<br>
        Will be replaced with real ERCOT price data when implemented.
    </div>
    """, unsafe_allow_html=True)
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
        df['color'] = df['price_quantile'].map(quantile_colors)
        # Dot radius by price (normalize for visual effect)
        min_price = df['price_cperkwh'].min()
        max_price = df['price_cperkwh'].max()
        df['radius'] = 30 + 70 * (df['price_cperkwh'] - min_price) / (max_price - min_price)

        # Ensure all tooltip fields are strings
        for col in ["price_cperkwh", "price_quantile"]:
            if col in df.columns:
                df[col] = df[col].astype(str)
        tooltip = {
            "html": "<b>ERCOT Node</b><br/>Price: ${price_cperkwh} ¢/kWh<br/>Level: {price_quantile}",
            "style": {
                "backgroundColor": "white",
                "color": "black",
                "fontSize": "14px",
                "borderRadius": "6px",
                "padding": "8px 12px",
                "boxShadow": "0 2px 8px rgba(0,0,0,0.15)"
            }
        }

        # Define view state for Texas
        view_state = pdk.ViewState(
            latitude=31.0,
            longitude=-99.0,
            zoom=5.2,
            pitch=0,
            min_zoom=5.2,
            max_zoom=5.2,
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
        # Render map
        deck = pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            map_style='mapbox://styles/mapbox/light-v10',  # White background like generation map
            views=[pdk.View(type='MapView', controller=False)],
            tooltip=tooltip  # type: ignore
        )
        st.pydeck_chart(deck, height=450)
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
