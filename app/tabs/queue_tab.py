"""
ERCOT Interconnection Queue Tab

Displaying projects in the ERCOT interconnection queue with visualization and data.
"""

import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.express as px
import sys
from pathlib import Path
from typing import Any, cast

# Add parent directory to path for local imports
sys.path.append(str(Path(__file__).parent.parent))

# Local imports after path modification  # noqa: E402
from utils.loaders import load_parquet, get_last_updated  # noqa: E402
from utils.data_sources import render_data_source_footer  # noqa: E402
from utils.colors import get_fuel_color_hex  # noqa: E402

def create_map_data(data):
    """Create properly formatted data for the map visualization."""
    # Ensure lat/lon are numeric and valid
    data = data.copy()
    data['lat'] = pd.to_numeric(data['lat'], errors='coerce')
    data['lon'] = pd.to_numeric(data['lon'], errors='coerce')
    data = data.dropna(subset=['lat', 'lon'])
    # Filter for Texas (rough boundaries)
    texas_projects = data[
        (data['lat'] >= 25.8) & 
        (data['lat'] <= 36.5) &
        (data['lon'] >= -106.6) & 
        (data['lon'] <= -93.5)
    ].copy()
    
    # Add colors based on fuel type
    def get_color(fuel_type):
        try:
            hex_color = get_fuel_color_hex(fuel_type)
            # Convert hex to RGB
            if hex_color.startswith('#'):
                hex_color = hex_color[1:]
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16) 
            b = int(hex_color[4:6], 16)
            return [r, g, b, 200]
        except:
            return [30, 54, 93, 200]  # Default blue
    
    texas_projects['color'] = texas_projects['fuel'].apply(get_color)
    
    # Scale point sizes based on capacity
    if 'capacity_mw' in texas_projects.columns:
        capacity_col = 'capacity_mw'
    elif 'max_capacity_mw' in texas_projects.columns:
        capacity_col = 'max_capacity_mw'
    else:
        capacity_col = texas_projects.select_dtypes(include=['number']).columns[0]
    
    # Coerce capacity column to numeric to avoid type issues
    texas_projects[capacity_col] = pd.to_numeric(texas_projects[capacity_col], errors='coerce').fillna(0)
    
    max_cap = texas_projects[capacity_col].max()
    min_cap = texas_projects[capacity_col].min()
    
    if max_cap > min_cap:
        normalized = (texas_projects[capacity_col] - min_cap) / (max_cap - min_cap)
        texas_projects['radius'] = 5 + normalized * 15
    else:
        texas_projects['radius'] = 10
        
    return texas_projects, capacity_col

def render():
    """Render the ERCOT Interconnection Queue tab."""
    
    # Default last_update to avoid footer errors on exceptions
    last_update: str = "Unknown"
    
    # Hero section with TAB branding
    st.markdown(
        """
        <div style="margin-bottom: 2rem;">
            <h2 style="margin-bottom:4px; color:#1B365D; font-weight:800;">
                ERCOT Interconnection Queue
            </h2>
            <div style="height: 6px; width: 140px; background: linear-gradient(90deg,#1B365D,#C8102E); border-radius: 4px; margin: 6px 0 18px 0;"></div>
            <div style="color:#0B1939; opacity:0.85; font-size:0.98rem; margin-top:2px;">
                Energy generation projects awaiting grid interconnection in Texas
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        # Load data
        data = load_parquet('queue.parquet', 'queue')
        last_update = get_last_updated(data)
        
        if data is None or data.empty:
            st.error("No queue data available")
            return
        
        # Create map data
        texas_projects, capacity_col = create_map_data(data)
        
        if texas_projects.empty:
            st.warning("No projects found within Texas boundaries")
            return
        
        # Summary statistics
        total_projects = len(texas_projects)
        total_capacity = texas_projects[capacity_col].sum()
        
        # Display key metrics with hover effects
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-card-title">Total Projects</div>
                <div class="metric-card-value">{total_projects:,}</div>
                <div class="metric-card-subtitle">In Interconnection Queue</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-card-title">Total Capacity</div>
                <div class="metric-card-value">{total_capacity:,.0f} MW</div>
                <div class="metric-card-subtitle">Planned Generation Capacity</div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            avg_capacity = total_capacity / total_projects if total_projects > 0 else 0
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-card-title">Average Project Size</div>
                <div class="metric-card-value">{avg_capacity:.1f} MW</div>
                <div class="metric-card-subtitle">Mean Capacity per Project</div>
            </div>
            """, unsafe_allow_html=True)
        with col4:
            # Find largest project
            largest_idx = texas_projects[capacity_col].idxmax()
            largest_project = texas_projects.loc[largest_idx]
            project_name = largest_project['project_name']
            display_name = project_name[:15] + ("..." if len(project_name) > 15 else "")
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-card-title">Largest Project</div>
                <div class="metric-card-value" style="font-size: 1.4rem;">{display_name}</div>
                <div class="metric-card-subtitle">{largest_project[capacity_col]:,.0f} MW</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Project map
        st.subheader("Project Locations")
        
        # Create map layer
        layer = pdk.Layer(
            'ScatterplotLayer',
            data=texas_projects,
            get_position=['lon', 'lat'],
            get_color='color',
            get_radius='radius',
            pickable=True,
            stroked=True,
            filled=True,
            radius_scale=1,
            radius_min_pixels=3,
            radius_max_pixels=20,
            get_line_color=[255, 255, 255, 150],
        )
        
        # Map view
        view_state = pdk.ViewState(
            latitude=31.0,
            longitude=-99.9,
            zoom=6.5,
            pitch=0
        )
        
        # Ensure optional columns used in tooltip exist
        if 'county' not in texas_projects.columns:
            texas_projects['county'] = 'Unknown'

        # Tooltip (pydeck accepts dict at runtime; cast for type checker)
        deck_tooltip: dict[str, Any] = {
            'html': f'<b>{{project_name}}</b><br/>Fuel: {{fuel}}<br/>Capacity: {{{capacity_col}}} MW<br/>County: {{county}}',
            'style': {'backgroundColor': 'steelblue', 'color': 'white'}
        }
        
        # Render map - COMPACT HEIGHT
        st.pydeck_chart(pdk.Deck(
            map_style='mapbox://styles/mapbox/light-v9',
            initial_view_state=view_state,
            layers=[layer],
            tooltip=cast(Any, deck_tooltip)
        ), height=400)
        
        # Queue Capacity by Fuel Type - Full width horizontal bar chart
        st.subheader("Queue Capacity by Fuel Type")
        
        # Calculate fuel breakdown
        fuel_capacity = texas_projects.groupby('fuel')[capacity_col].sum().sort_values(ascending=False)
        
        # Create horizontal bar chart with custom colors
        fuel_df = pd.DataFrame({
            'Fuel Type': fuel_capacity.index,
            'Capacity (MW)': fuel_capacity.values
        })
        
        # Create Plotly horizontal bar chart
        fig = px.bar(
            fuel_df,
            x='Capacity (MW)',
            y='Fuel Type',
            orientation='h',
            title="",
            color='Fuel Type',
            color_discrete_map={fuel: get_fuel_color_hex(fuel) for fuel in fuel_capacity.index}
        )
        
        # Update layout for better appearance with thicker bars
        fig.update_layout(
            height=max(350, len(fuel_capacity) * 60),  # Increased height for thicker bars
            showlegend=False,
            yaxis={'categoryorder': 'total ascending'},
            xaxis_title="Capacity (MW)",
            yaxis_title="",
            margin=dict(l=0, r=0, t=20, b=0),
            bargap=0.3  # Reduced gap between bars to make them appear thicker
        )
        
        # Calculate percentages correctly for each fuel type
        total_fuel_capacity = fuel_capacity.sum()
        percentages = (fuel_capacity.values / total_fuel_capacity * 100)
        
        # Add hover template with percentages
        fig.update_traces(
            hovertemplate='<b>%{y}</b><br>Capacity: %{x:,.0f} MW<br>Share: %{customdata:.1f}%<extra></extra>',
            customdata=percentages
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Project list
        st.subheader("All Projects in Queue")
        
        # Prepare display dataframe
        display_df = texas_projects[['project_name', 'fuel', capacity_col, 'county', 'status']].copy()
        display_df = display_df.rename(columns={
            'project_name': 'Project Name',
            'fuel': 'Fuel Type',
            capacity_col: 'Capacity (MW)',
            'county': 'County',
            'status': 'Status'
        })
        display_df = display_df.sort_values('Capacity (MW)', ascending=False)
        
        # Search and filter
        search_term = st.text_input("Search projects:", placeholder="Enter project name, fuel type, or county...")
        if search_term:
            mask = display_df.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)
            display_df = display_df[mask]
        
        # Fuel type filter
        fuel_options = ['All'] + sorted(texas_projects['fuel'].unique().tolist())
        selected_fuel = st.selectbox("Filter by fuel type:", fuel_options)
        if selected_fuel != 'All':
            display_df = display_df[display_df['Fuel Type'] == selected_fuel]
        
        # Display projects table - COMPACT HEIGHT
        st.dataframe(
            display_df,
            hide_index=True,
            height=400,
            column_config={
                "Capacity (MW)": st.column_config.NumberColumn(
                    "Capacity (MW)",
                    format="%.0f"
                )
            }
        )
        
        st.caption(f"Showing {len(display_df)} of {total_projects} projects")
        
        # Technical notes
        with st.expander("Data Notes"):
            st.markdown(f"""
            **Data Source:** ERCOT Interconnection Queue Reports
            
            **Coverage:** All projects in various stages of the interconnection study process
            
            **Project Status:** Projects shown represent planned future generation capacity. 
            Not all projects will reach commercial operation.
            
            **Last Updated:** {last_update[:19]}Z
            
            **Map Notes:** Point size represents project capacity. Colors indicate fuel type.
            Geographic filtering ensures only Texas projects are displayed.
            """)
    
    except Exception as e:
        st.error(f"Error loading queue data: {str(e)}")
        
        # Debug info
        try:
            debug_data = load_parquet('queue.parquet', 'queue')
            if debug_data is not None:
                st.info("Available columns:")
                st.write(list(debug_data.columns))
        except:
            pass
    
    # Footer
    render_data_source_footer('queue', last_update)
