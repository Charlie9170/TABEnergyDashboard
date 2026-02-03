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
import plotly.graph_objects as go
from datetime import datetime

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from utils.loaders import load_parquet, get_last_updated
from utils.data_sources import render_data_source_footer
from utils.export import create_download_button
from utils.advocacy import render_advocacy_message


def render():
    """Render the Price Map tab with real-time ERCOT LMP data."""
    
    # Header - ultra compact
    st.markdown("### ERCOT Real-Time Price Map")
    
    # Compact advocacy message - single line, non-intrusive
    st.markdown("""
    <div style="padding: 8px 12px; background-color: #f8f9fa; border-left: 3px solid #1f4788; 
                margin: 12px 0 20px 0; font-size: 14px; color: #4b5563; line-height: 1.5;">
        <strong>TAB Policy:</strong> Texas Association of Business supports competitive wholesale markets 
        that keep Texas energy costs among the lowest in the nation. 
        <a href="https://www.txbiz.org/policy-priorities/energy/" target="_blank" 
           style="color: #1f4788; text-decoration: none; font-weight: 500;">Learn more →</a>
    </div>
    """, unsafe_allow_html=True)
    
    # Professional styling for view toggle (Option A: Minimal Professional)
    st.markdown("""
    <style>
        /* Professional view toggle styling */
        div[data-testid="stRadio"] > div {
            gap: 1rem;
        }
        div[data-testid="stRadio"] label {
            font-size: 14px;
            font-weight: 400;
            color: #333333;
            padding: 0.25rem 0.5rem;
        }
        /* Reduce spacing around map for maximum vertical space */
        .element-container:has(iframe) {
            margin-top: 0.5rem;
            margin-bottom: 0.5rem;
        }
        /* View toggle container styling */
        .view-toggle-row {
            padding: 12px 0;
            margin-bottom: 16px;
        }
        .view-label {
            color: #555555;
            font-weight: 500;
            font-size: 14px;
        }
        .view-description {
            color: #777777;
            font-size: 13px;
            line-height: 1.4;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Professional single-line toggle (no emoji, clean typography)
    col1, col2, col3 = st.columns([1.5, 3, 5])
    with col1:
        st.markdown('<span class="view-label">Display Mode:</span>', unsafe_allow_html=True)
    with col2:
        view_mode = st.radio(
            "view_mode",
            ["Major Hubs (9)", "All Settlement Points (15)"],
            horizontal=True,
            key="price_map_view",
            label_visibility="collapsed"
        )
    with col3:
        if "Major Hubs" in view_mode:
            st.markdown('<span class="view-description">9 load zones • Faster rendering • Core coverage</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="view-description">15 settlement points • Complete ERCOT coverage • 6 strategic nodes</span>', unsafe_allow_html=True)
    
    try:
        # Load data with error handling
        df = load_parquet("price_map.parquet", "price_map", allow_empty=True)
        
        # Check if data is empty
        if df is None or len(df) == 0:
            st.warning("⚠️ **No price data available**")
            st.info("Run the ETL script to fetch real-time ERCOT LMP data.")
            st.code("python etl/ercot_lmp_etl.py", language="bash")
            return
        
        # Filter data based on view mode
        if view_mode == "Major Hubs (9)":
            if 'tier' in df.columns:
                df = df[df['tier'] == 'hub'].copy()
            else:
                # Fallback if tier column doesn't exist
                pass
        # else: show all settlement points (no filtering needed)
        
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
            min_zone = df.loc[df[price_col].idxmin(), 'region'] if 'region' in df.columns else 'N/A'
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-card-title">Lowest Price</div>
                <div class="metric-card-value">${min_price_val:.2f}/MWh</div>
                <div class="metric-card-subtitle">{min_zone}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            max_price_val = df[price_col].max()
            max_zone = df.loc[df[price_col].idxmax(), 'region'] if 'region' in df.columns else 'N/A'
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
        
        st.markdown("---")
        
        # Create Plotly Scattermapbox for reliable tooltips
        # Color scale based on price quantiles (coral/red matching other tabs)
        color_map = {
            'Very Low': '#ff9682',   # Light coral
            'Low': '#ff7864',        # Coral
            'Medium': '#ff5a46',     # Red-coral
            'High': '#e63c32',       # Deep red
            'Very High': '#c81e1e',  # Dark red
        }
        
        # Map quantiles to colors
        df['marker_color'] = df['price_quantile'].map(color_map)
        
        # Create Plotly figure
        fig = go.Figure()
        
        # Add scatter points for each price level (for legend)
        for level in ['Very Low', 'Low', 'Medium', 'High', 'Very High']:
            df_level = df[df['price_quantile'] == level]
            if len(df_level) > 0:
                fig.add_trace(go.Scattermapbox(
                    lat=df_level['lat'],
                    lon=df_level['lon'],
                    mode='markers',
                    marker=dict(
                        size=16,
                        color=color_map[level],
                        opacity=0.8,
                    ),
                    text=df_level['region'],
                    customdata=df_level[['avg_price', 'price_cperkwh', 'price_quantile']],
                    hovertemplate=(
                        '<b>%{text}</b><br>'
                        'Price: $%{customdata[0]:.2f}/MWh<br>'
                        '(%{customdata[1]:.2f} ¢/kWh)<br>'
                        'Level: %{customdata[2]}'
                        '<extra></extra>'
                    ),
                    name=level,
                    showlegend=True
                ))
        
        # Update layout for Texas-focused map
        fig.update_layout(
            mapbox=dict(
                style='carto-positron',  # Clean white background to match other tabs
                center=dict(lat=31.0, lon=-99.5),
                zoom=5.2
            ),
            height=500,
            margin=dict(l=0, r=0, t=0, b=0),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=0.02,
                xanchor="center",
                x=0.5,
                bgcolor="rgba(255, 255, 255, 0.9)",
                bordercolor="rgba(0, 0, 0, 0.2)",
                borderwidth=1
            ),
            hovermode='closest'
        )
        
        # Render Plotly map
        st.plotly_chart(fig, use_container_width=True)
        
        # Data status indicator - standardized format matching other tabs
        if 'last_updated' in df.columns:
            last_update = pd.to_datetime(df['last_updated'].iloc[0])
            timestamp = last_update.strftime('%Y-%m-%d %H:%M:%S')
            st.success(f"**ERCOT Real-Time LMP** - Last Updated: {timestamp}")
        
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
