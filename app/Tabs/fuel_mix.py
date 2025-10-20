"""ERCOT Fuel Mix Tab - Displays hourly fuel mix data from EIA."""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from app.utils import load_fuel_mix_data, FUEL_COLORS

def render_fuel_mix_tab():
    """Render the ERCOT Fuel Mix tab."""
    st.header("ERCOT Fuel Mix")
    st.markdown("Hourly electricity generation by fuel source from EIA data (ERCO region)")
    
    try:
        # Load fuel mix data
        df = load_fuel_mix_data()
        
        if df.empty:
            st.warning("No fuel mix data available. Run the ETL process to fetch data.")
            return
        
        # Display data info
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Records", len(df))
        with col2:
            if not df.empty:
                st.metric("Latest Data", df['period'].max().strftime('%Y-%m-%d %H:%M'))
        with col3:
            if not df.empty:
                st.metric("Fuel Types", df['fuel'].nunique())
        
        # Date range selector
        if not df.empty:
            min_date = df['period'].min().date()
            max_date = df['period'].max().date()
            
            date_range = st.date_input(
                "Select Date Range",
                value=(max_date, max_date),
                min_value=min_date,
                max_value=max_date
            )
            
            if len(date_range) == 2:
                start_date, end_date = date_range
                mask = (df['period'].dt.date >= start_date) & (df['period'].dt.date <= end_date)
                filtered_df = df[mask]
            else:
                filtered_df = df
            
            # Create stacked area chart
            if not filtered_df.empty:
                # Pivot data for stacked area chart
                pivot_df = filtered_df.pivot_table(
                    index='period',
                    columns='fuel',
                    values='value_mwh',
                    aggfunc='sum'
                ).fillna(0)
                
                # Create figure
                fig = go.Figure()
                
                for fuel in pivot_df.columns:
                    color = FUEL_COLORS.get(fuel.lower(), '#95a5a6')
                    fig.add_trace(go.Scatter(
                        x=pivot_df.index,
                        y=pivot_df[fuel],
                        mode='lines',
                        name=fuel.title(),
                        stackgroup='one',
                        fillcolor=color,
                        line=dict(width=0.5, color=color),
                        hovertemplate='<b>%{fullData.name}</b><br>%{y:,.0f} MWh<extra></extra>'
                    ))
                
                fig.update_layout(
                    title='ERCOT Fuel Mix Over Time',
                    xaxis_title='Time',
                    yaxis_title='Generation (MWh)',
                    hovermode='x unified',
                    height=500,
                    template='plotly_dark',
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    )
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Show summary statistics
                st.subheader("Summary Statistics")
                summary = filtered_df.groupby('fuel')['value_mwh'].agg(['sum', 'mean', 'max']).round(2)
                summary.columns = ['Total (MWh)', 'Average (MWh)', 'Peak (MWh)']
                st.dataframe(summary, use_container_width=True)
                
                # Show raw data (expandable)
                with st.expander("View Raw Data"):
                    st.dataframe(filtered_df.sort_values('period', ascending=False), use_container_width=True)
        
    except Exception as e:
        st.error(f"Error loading fuel mix data: {str(e)}")
