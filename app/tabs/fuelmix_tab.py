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
from utils.colors import FUEL_COLORS_HEX, is_renewable


def render():
    """Render the Fuel Mix tab."""
    
    # Header
    st.header("ERCOT Fuel Mix")
    st.markdown(
        "Hourly electricity generation by fuel type across the ERCOT grid. "
        "Data shows the energy sources powering Texas in real-time."
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
            
            st.markdown(f"""
            <div class="kpi-card">
                <p class="kpi-value">{avg_hourly:,.0f} MWh</p>
                <p class="kpi-label">Average Hourly Generation</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            # Renewable share
            df['is_renewable'] = df['fuel'].apply(is_renewable)
            renewable_total = df[df['is_renewable']]['value_mwh'].sum()
            total = df['value_mwh'].sum()
            renewable_share = (renewable_total / total * 100) if total > 0 else 0
            
            st.markdown(f"""
            <div class="kpi-card">
                <p class="kpi-value">{renewable_share:.1f}%</p>
                <p class="kpi-label">Renewable Energy Share</p>
            </div>
            """, unsafe_allow_html=True)
        
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
            fig.add_trace(go.Scatter(
                x=pivot_df.index,
                y=pivot_df[fuel],
                name=fuel.capitalize(),
                mode='lines',
                stackgroup='one',
                fillcolor=FUEL_COLORS_HEX.get(fuel.upper(), '#64748b'),
                line=dict(width=0.5, color=FUEL_COLORS_HEX.get(fuel.upper(), '#64748b')),
                hovertemplate='%{y:,.0f} MWh<extra></extra>',
            ))
        
        # Update layout with dark theme
        fig.update_layout(
            title="ERCOT Generation by Fuel Type (Last 7 Days)",
            xaxis_title="Time (Central Time)",
            yaxis_title="Generation (MWh)",
            hovermode='x unified',
            height=500,
            template="plotly_dark",
            paper_bgcolor='#0f172a',
            plot_bgcolor='#111827',
            font=dict(color='#e5e7eb'),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.2,
                xanchor="center",
                x=0.5
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Footer
        last_updated = get_last_updated(df)
        st.markdown(f"""
        <div class="footer">
            <strong>Source:</strong> U.S. Energy Information Administration (EIA) • 
            <strong>Last Updated:</strong> {last_updated}
        </div>
        """, unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"Error loading fuel mix data: {str(e)}")
        st.info("Please ensure the ETL script has been run to generate the data file.")
