"""
Price Map Tab - ERCOT Real-Time LMP Visualization

Displays real-time electricity prices across 15 ERCOT settlement points
(9 major hubs + 6 strategic nodes).
Source: ERCOT public real-time SPP page; dashboard ETL every 6 hours.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from utils.loaders import load_parquet, get_last_updated
from utils.data_sources import render_data_source_footer, render_freshness_banner
from utils.export import create_download_button
from utils.advocacy import render_advocacy_message


def render():
    """Render the Price Map tab with real-time ERCOT LMP data."""
    
    # Header - ultra compact
    st.subheader(
        "ERCOT Real-Time Price Map",
        help="Settlement point prices at 15 ERCOT locations (9 major hubs and 6 strategic nodes).",
    )
    
    # Compact advocacy message - single line, non-intrusive
    st.markdown("""
    <div style="padding: 8px 12px; background-color: #f8f9fa; border-left: 3px solid #1f4788; 
                margin: 12px 0 8px 0; font-size: 14px; color: #4b5563; line-height: 1.5;">
        <strong>TAB Policy:</strong> Texas Association of Business supports competitive wholesale markets 
        that keep Texas energy costs among the lowest in the nation.
    </div>
    """, unsafe_allow_html=True)
    
    # Minimal container styling (view toggle removed - always shows all 15
    # settlement points, ERCOT's public real-time SPP source ceiling)
    st.markdown("""
    <style>
        /* Reduce spacing around map for maximum vertical space */
        .element-container:has(iframe) {
            margin-top: 0.5rem;
            margin-bottom: 0.5rem;
        }
    </style>
    """, unsafe_allow_html=True)
    
    try:
        # Load data with error handling
        df = load_parquet("price_map.parquet", "price_map", allow_empty=True)
        
        # Check if data is empty
        if df is None or len(df) == 0:
            st.warning("⚠️ **No price data available**")
            st.info("Run the ETL script to fetch real-time ERCOT LMP data.")
            st.code("python etl/ercot_lmp_etl.py", language="bash")
            return
        
        # Always show all 15 settlement points (9 hubs + 6 strategic nodes).
        # The "Major Hubs (9)" toggle was removed since ERCOT's public
        # real-time SPP source caps out at exactly 15 settlement points —
        # there was no meaningful "reduced" view once that ceiling is known.
        
        # Use avg_price column (from ERCOT aggregation)
        price_col = 'avg_price' if 'avg_price' in df.columns else 'price_cperkwh'
        
        # Calculate price quantiles for color coding.
        # NOTE: pd.qcut's duplicates='drop' silently collapses bin *edges*
        # when the underlying data has ties (e.g. flat/placeholder pricing
        # with zero variance), but does NOT shrink a fixed-length labels
        # list to match — this previously crashed with "Bin labels must be
        # one fewer than the number of bin edges" whenever price data had
        # low variance. Fix: generate labels sized to the actual bin count
        # actually produced, falling back to a single "Normal" bucket when
        # all prices are identical.
        quantile_colors_full = {
            'Very Low': [255, 150, 130, 180],   # Light coral
            'Low': [255, 120, 100, 180],        # Coral
            'Medium': [255, 90, 70, 180],       # Red-coral
            'High': [230, 60, 50, 180],         # Deep red
            'Very High': [200, 30, 30, 180],    # Dark red
        }
        label_order = ['Very Low', 'Low', 'Medium', 'High', 'Very High']

        if df[price_col].nunique() <= 1:
            # Zero-variance data: every zone has the same price, so a single
            # "Normal" bucket is the only meaningful category.
            df['price_quantile'] = 'Normal'
            quantile_colors = {'Normal': quantile_colors_full['Medium']}
        else:
            bins = pd.qcut(df[price_col], q=5, duplicates='drop')
            n_bins = bins.cat.categories.size
            # Pick an evenly-spaced subset of the 5 canonical labels sized
            # to however many distinct bins the data actually supports.
            if n_bins >= len(label_order):
                labels = label_order
            else:
                step = (len(label_order) - 1) / (n_bins - 1) if n_bins > 1 else 0
                labels = [label_order[round(i * step)] for i in range(n_bins)]
            df['price_quantile'] = pd.qcut(
                df[price_col], q=5, labels=labels, duplicates='drop'
            ).astype(str)
            quantile_colors = {lbl: quantile_colors_full[lbl] for lbl in labels}
        
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
        
        # Create Plotly Scattermapbox for reliable tooltips
        # Color scale based on price quantiles (coral/red matching other tabs)
        color_map = {
            'Very Low': '#ff9682',   # Light coral
            'Low': '#ff7864',        # Coral
            'Medium': '#ff5a46',     # Red-coral
            'Normal': '#ff5a46',     # Uniform-price snapshot (zero spread)
            'High': '#e63c32',       # Deep red
            'Very High': '#c81e1e',  # Dark red
        }
        
        # Map quantiles to colors
        df['marker_color'] = df['price_quantile'].map(color_map)
        
        # Create Plotly figure
        fig = go.Figure()
        
        # Plot every quantile label actually present — including 'Normal'
        # when all zones share the same price (previously skipped, blank map).
        legend_order = ['Very Low', 'Low', 'Medium', 'Normal', 'High', 'Very High']
        levels_present = [lvl for lvl in legend_order if lvl in set(df['price_quantile'])]
        for level in levels_present:
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

        if 'last_updated' in df.columns:
            last_update = pd.to_datetime(df['last_updated'].iloc[0])
            render_freshness_banner(
                "ERCOT Real-Time LMP",
                last_update.strftime('%Y-%m-%d %H:%M:%S'),
            )
        
        # Data Export Section
        st.markdown("---")
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("**Download Real-Time LMP Data**")
        with col2:
            create_download_button(
                df=df,
                filename_prefix="ercot_lmp_realtime",
                label="Download LMP Data"
            )
        
        data_through = None
        if 'oper_day' in df.columns and 'interval_end' in df.columns:
            oper_day = str(df['oper_day'].iloc[0])
            interval_end = str(df['interval_end'].iloc[0]).strip()
            if interval_end.isdigit() and len(interval_end) <= 4:
                padded = interval_end.zfill(4)
                interval_end = f"{padded[:2]}:{padded[2:]}"
            data_through = f"{oper_day}, interval ending {interval_end}"
        render_data_source_footer(
            'price_map',
            get_last_updated(df),
            data_through=data_through,
        )
        
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
        st.code("python etl/ercot_lmp_etl.py", language="bash")
