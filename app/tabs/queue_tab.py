"""
Interconnection Queue Tab - Proposed Generation Projects

Displays projects in the ERCOT interconnection queue:
- Interactive map of proposed projects colored by fuel type
- Bar chart showing proposed capacity by fuel type
- Status breakdown of projects in the pipeline
"""

import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.graph_objects as go

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from utils.loaders import load_parquet, get_last_updated
from utils.colors import get_fuel_color_rgba, FUEL_COLORS_HEX


def render():
    """Render the Interconnection Queue tab."""
    
    # Header
    st.header("ERCOT Interconnection Queue")
    st.markdown(
        "Proposed generation projects seeking connection to the ERCOT grid. "
        "Projects are color-coded by fuel type, showing the future of Texas energy infrastructure."
    )
    
    try:
        # Load data
        df = load_parquet("queue.parquet", "queue")
        
        # Add color column based on fuel type (using list comprehension to avoid pandas indexing issues)
        df['color'] = [get_fuel_color_rgba(f, alpha=200) for f in df['fuel']]
        
        # Scale radius by proposed capacity (30m per MW, capped at 1500m)
        df['radius'] = df['proposed_mw'].apply(lambda x: min(x * 30, 1500))
        
        # Summary stats
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_proposed = df['proposed_mw'].sum()
            st.markdown(f"""
            <div class="kpi-card">
                <p class="kpi-value">{total_proposed:,.0f} MW</p>
                <p class="kpi-label">Total Proposed Capacity</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            project_count = len(df)
            st.markdown(f"""
            <div class="kpi-card">
                <p class="kpi-value">{project_count:,}</p>
                <p class="kpi-label">Projects in Queue</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            fuel_types = df['fuel'].nunique()
            st.markdown(f"""
            <div class="kpi-card">
                <p class="kpi-value">{fuel_types}</p>
                <p class="kpi-label">Fuel Types</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("")  # Spacing
        
        # Two-column layout for map and chart
        col_map, col_chart = st.columns([2, 1])
        
        with col_map:
            st.markdown("#### Project Locations")
            
            # Create pydeck map
            view_state = pdk.ViewState(
                latitude=df['lat'].mean() if len(df) > 0 else 31.0,
                longitude=df['lon'].mean() if len(df) > 0 else -99.0,
                zoom=5.5,
                pitch=0,
            )
            
            # Convert to list of dicts for pydeck (avoids JSON serialization issues)
            data_for_pydeck = df.to_dict('records')
            
            # ScatterplotLayer for queue projects
            layer = pdk.Layer(
                'ScatterplotLayer',
                data=data_for_pydeck,
                get_position='[lon, lat]',
                get_color='color',
                get_radius='radius',
                pickable=True,
                opacity=0.6,
                stroked=True,
                filled=True,
                line_width_min_pixels=1,
            )
            
            # Tooltip configuration
            tooltip = {
                "html": """
                <b>{project_name}</b><br/>
                <b>Fuel:</b> {fuel}<br/>
                <b>Capacity:</b> {proposed_mw:.1f} MW<br/>
                <b>Status:</b> {status}
                """,
                "style": {
                    "backgroundColor": "#1f2937",
                    "color": "#e5e7eb",
                    "border": "1px solid #374151",
                    "borderRadius": "4px",
                    "padding": "8px"
                }
            }
            
            # Render map
            deck = pdk.Deck(
                layers=[layer],
                initial_view_state=view_state,
                tooltip=tooltip,
                map_style='mapbox://styles/mapbox/dark-v10',
            )
            
            st.pydeck_chart(deck, use_container_width=True)
        
        with col_chart:
            st.markdown("#### Proposed Capacity by Fuel")
            
            # Group by fuel type
            fuel_capacity = df.groupby('fuel')['proposed_mw'].sum().sort_values(ascending=True)
            
            # Create horizontal bar chart
            fig = go.Figure()
            
            colors = [FUEL_COLORS_HEX.get(fuel.upper(), '#64748b') for fuel in fuel_capacity.index]
            
            fig.add_trace(go.Bar(
                y=fuel_capacity.index,
                x=fuel_capacity.values,
                orientation='h',
                marker=dict(color=colors),
                text=fuel_capacity.values,
                texttemplate='%{text:,.0f} MW',
                textposition='outside',
                hovertemplate='<b>%{y}</b><br>%{x:,.0f} MW<extra></extra>',
            ))
            
            fig.update_layout(
                height=400,
                template="plotly_dark",
                paper_bgcolor='#0f172a',
                plot_bgcolor='#111827',
                font=dict(color='#e5e7eb'),
                xaxis_title="Proposed Capacity (MW)",
                yaxis_title="",
                showlegend=False,
                margin=dict(l=0, r=80, t=20, b=40),
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        # Status breakdown
        if 'status' in df.columns:
            st.markdown("### Project Status Breakdown")
            status_counts = df.groupby('status')['proposed_mw'].agg(['count', 'sum']).reset_index()
            status_counts.columns = ['Status', 'Project Count', 'Total Capacity (MW)']
            status_counts['Total Capacity (MW)'] = status_counts['Total Capacity (MW)'].round(1)
            
            st.dataframe(
                status_counts,
                use_container_width=True,
                hide_index=True,
            )
        
        # Footer
        last_updated = get_last_updated(df)
        st.markdown(f"""
        <div class="footer">
            <strong>Source:</strong> ERCOT Interconnection Queue • 
            <strong>Last Updated:</strong> {last_updated}
        </div>
        """, unsafe_allow_html=True)
        
    except Exception as e:
        st.error(f"Error loading interconnection queue data: {str(e)}")
        st.info("Please ensure the ETL script has been run to generate the data file.")
