"""
Fuel Mix Tab - ERCOT Electricity Generation by Fuel Type

Displays hourly electricity generation data from ERCOT by fuel type:
- Stacked area chart showing generation over time
- KPIs for total generation and renewable share
- Data sourced from EIA API (respondent=ERCO)
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from utils.loaders import load_parquet, get_last_updated
from utils.colors import FUEL_COLORS_HEX, is_renewable, get_fuel_color_hex
from utils.data_sources import render_data_source_footer


def render():
    """Render the Fuel Mix tab."""
    
    # Local styles for a clean TAB-branded hero and KPI pills
    st.markdown(
        """
        <style>
            .fuelmix-hero .accent-bar { height: 6px; width: 140px; background: linear-gradient(90deg,#1B365D,#C8102E); border-radius: 4px; margin: 6px 0 18px 0; }
            .fuelmix-hero .subtitle { color:#0B1939; opacity:0.85; font-size:0.98rem; margin-top:2px; }
            .status-pill { display:inline-block; background:#F5F7FA; color:#0B1939; border-left:4px solid #1B365D; padding:6px 10px; border-radius:6px; font-size:0.85rem; font-weight:600; }
            .kpi-pill { background:#FFFFFF; border:1px solid #E5E7EB; border-left:4px solid #1B365D; border-radius:10px; padding:12px 16px; }
            .kpi-value { font-size:1.6rem; font-weight:700; color:#1B365D; margin:0; }
            .kpi-label { font-size:0.9rem; color:#6B7280; margin:4px 0 0 0; font-weight:500; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Hero section
    st.markdown(
        """
        <div class="fuelmix-hero">
            <h2 style="margin-bottom:4px; color:#1B365D; font-weight:800;">ERCOT Fuel Mix</h2>
            <div class="accent-bar"></div>
            <div class="subtitle">Hourly electricity generation by fuel type across the ERCOT grid.</div>
            <div class="status-pill" style="margin-top:10px;">🟢 Live data · Auto-updated via EIA every 6 hours</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    try:
        # Load data
        df = load_parquet("fuelmix.parquet", "fuelmix")
        
        # Convert period to Central Time for display
        df['period_ct'] = df['period'].dt.tz_convert('America/Chicago')
        
        # Calculate KPIs
        col1, col2 = st.columns(2)
        
        with col1:
            # Average hourly total generation
            total_by_period = df.groupby('period')['value_mwh'].sum()
            avg_hourly = total_by_period.mean()
            st.markdown(
                f"""
                <div class="kpi-pill">
                    <p class="kpi-value">{avg_hourly:,.0f} MWh</p>
                    <p class="kpi-label">Average Hourly Generation</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        
        with col2:
            # Renewable share
            df['is_renewable'] = df['fuel'].apply(is_renewable)
            renewable_total = df[df['is_renewable']]['value_mwh'].sum()
            total = df['value_mwh'].sum()
            renewable_share = (renewable_total / total * 100) if total > 0 else 0
            
            st.markdown(
                f"""
                <div class="kpi-pill">
                    <p class="kpi-value">{renewable_share:.1f}%</p>
                    <p class="kpi-label">Renewable Energy Share</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        
        st.markdown("")  # Spacing
        
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
        
        # Update layout - using global tab_theme from main.py
        fig.update_layout(
            title="ERCOT Generation by Fuel Type (Last 7 Days)",
            xaxis_title="Time (Central Time)",
            yaxis_title="Generation (MWh)",
            hovermode='x unified',
            height=500,
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
            xaxis=dict(title="Time (Central Time)", title_standoff=30),
            yaxis=dict(title="Generation (MWh)", title_standoff=10),
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Data source footer
        last_updated = get_last_updated(df)
        render_data_source_footer('fuelmix', last_updated)
        
    except Exception as e:
        st.error(f"Error loading fuel mix data: {str(e)}")
        st.info("Please ensure the ETL script has been run to generate the data file.")
