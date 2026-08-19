"""
Fuel Mix Tab - ERCOT Electricity Generation by Fuel Type

Displays hourly electricity generation data from ERCOT by fuel type:
- Stacked area chart showing generation over time
- KPIs for total generation and renewable share
- Data sourced from EIA API (respondent=ERCO)
"""

import logging
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from utils.loaders import load_parquet, get_last_updated
from utils.colors import is_renewable, get_fuel_color_hex
from utils.data_sources import format_ct, render_data_source_footer, render_freshness_banner
from utils.export import create_download_button

logger = logging.getLogger(__name__)


def render():
    """Render the Fuel Mix tab with comprehensive error handling."""
    
    # Minimal header matching other tabs - ultra compact
    st.subheader(
        "ERCOT Fuel Mix",
        help="Hourly electricity generation by fuel type across the ERCOT grid.",
    )
    
    # Compact advocacy message - single line, non-intrusive
    st.markdown("""
    <div style="padding: 8px 12px; background-color: #f8f9fa; border-left: 3px solid #1f4788; 
                margin: 12px 0 8px 0; font-size: 14px; color: #4b5563; line-height: 1.5;">
        <strong>TAB Policy:</strong> Texas Association of Business supports a diverse, reliable energy mix 
        that keeps electricity affordable and competitive for Texas businesses.
    </div>
    """, unsafe_allow_html=True)
    
    try:
        # Load data with graceful error handling
        df = load_parquet("fuelmix.parquet", "fuelmix", allow_empty=True)
        
        # Check if data is empty
        if df is None or len(df) == 0:
            logger.warning("Fuel mix data unavailable: fuelmix.parquet empty or missing")
            st.warning("Fuel mix data temporarily unavailable.")
            return
        
        # Convert period to Central Time for display
        df['period_ct'] = df['period'].dt.tz_convert('America/Chicago')
        
        # Calculate KPIs - Unified metric card style matching other tabs
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Average hourly total generation
            total_by_period = df.groupby('period')['value_mwh'].sum()
            avg_hourly = total_by_period.mean()
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-card-title">Average Hourly Generation</div>
                <div class="metric-card-value">{avg_hourly:,.0f} MWh</div>
                <div class="metric-card-subtitle">Last 7 Days</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            # Peak generation hour
            peak_generation = total_by_period.max()
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-card-title">Peak Generation</div>
                <div class="metric-card-value">{peak_generation:,.0f} MWh</div>
                <div class="metric-card-subtitle">Highest Demand Period</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            # Renewable share
            df['is_renewable'] = df['fuel'].apply(is_renewable)
            renewable_total = df[df['is_renewable']]['value_mwh'].sum()
            total = df['value_mwh'].sum()
            renewable_share = (renewable_total / total * 100) if total > 0 else 0
            
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-card-title">Renewable Energy Share</div>
                <div class="metric-card-value">{renewable_share:.1f}%</div>
                <div class="metric-card-subtitle">Solar, Wind, Hydro, Biomass</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("")  # Spacing
        
        # Section header matching other tabs
        st.subheader("ERCOT Generation by Fuel Type (Last 7 Days)")
        
        # Create stacked area chart with Plotly
        fig = go.Figure()
        
        # Pivot data for plotting
        pivot_df = df.pivot_table(
            index='period_ct',
            columns='fuel',
            values='value_mwh',
            aggfunc='sum'
        ).fillna(0)
        
        # Sort columns by average value (largest first) for better stacking
        col_order = pivot_df.mean().sort_values(ascending=False).index
        
        # Add traces for each fuel type
        for fuel in col_order:
            color_hex = get_fuel_color_hex(str(fuel))
            fig.add_trace(go.Scatter(
                x=pivot_df.index,
                y=pivot_df[fuel],
                name=fuel.capitalize(),
                mode='lines',
                stackgroup='one',
                fillcolor=color_hex,
                line=dict(width=0.8, color=color_hex),
                hovertemplate='%{y:,.0f} MWh<extra></extra>',
            ))
        
        # Update layout - clean and consistent
        fig.update_layout(
            xaxis_title="Time (Central Time)",
            yaxis_title="Generation (MWh)",
            hovermode='x unified',
            height=450,
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.25,
                xanchor="center",
                x=0.5,
                bgcolor="#FFFFFF",
                bordercolor="#E5E7EB",
                borderwidth=1,
                font=dict(size=12),
                traceorder="normal"
            ),
            margin=dict(t=60, r=20, b=120, l=60),
            xaxis=dict(
                title="Time (Central Time)", 
                title_standoff=30,
                tickformat="%b %d"  # Show only "Nov 5" without year
            ),
            yaxis=dict(title="Generation (MWh)", title_standoff=10),
        )
        
        st.plotly_chart(fig, use_container_width=True)

        render_freshness_banner(
            "ERCOT Fuel Mix Data",
            df['period'].max(),
            meaning="vintage",
        )
        
        # Data Export Section
        st.markdown("---")
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("**Download Data for Reports & Presentations**")
        with col2:
            create_download_button(
                df=df,
                filename_prefix="fuelmix_hourly",
                label="Download Fuel Mix Data"
            )
        
        latest_period = df['period'].max()
        render_data_source_footer(
            'fuelmix',
            get_last_updated(df),
            data_through=format_ct(latest_period) if pd.notna(latest_period) else None,
        )
        
    except KeyError:
        logger.exception("Fuel mix tab: missing required column")
        st.warning("Fuel mix data temporarily unavailable.")

    except pd.errors.EmptyDataError:
        logger.exception("Fuel mix tab: empty data file")
        st.warning("Fuel mix data temporarily unavailable.")

    except Exception:
        logger.exception("Fuel mix tab: unexpected error")
        st.warning("Fuel mix data temporarily unavailable.")
