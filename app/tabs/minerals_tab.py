"""
Minerals & Critical Minerals Tab - Texas REE and Critical Mineral Deposits

Displays Texas Rare Earth Elements (REEs) and Critical Minerals deposits
with development status classification and geographic visualization.
"""

import streamlit as st
import pandas as pd
import pydeck as pdk
import math
import json
from pathlib import Path
from typing import Optional

import sys
sys.path.append(str(Path(__file__).parent.parent))

from utils.loaders import load_parquet, get_last_updated, get_file_modification_time
from utils.data_sources import render_data_source_footer
from utils.colors import TAB_COLORS, NEUTRAL_COLORS
from utils.export import create_download_button
from utils.advocacy import render_advocacy_message
from utils.table_styling import apply_professional_table_style


# Development status color palette (TAB brand colors - refined)
STATUS_COLORS = {
    'Major': [200, 16, 46, 220],        # TAB Red (refined alpha)
    'Early': [255, 140, 0, 200],         # Warm Orange
    'Exploratory': [241, 196, 15, 180],  # Soft Gold
    'Discovery': [27, 54, 93, 160]       # TAB Navy (replaces gray)
}

STATUS_COLORS_HEX = {
    'Major': '#C8102E',          # TAB Red
    'Early': '#FF8C00',          # Orange
    'Exploratory': '#F1C40F',    # Soft Gold
    'Discovery': '#1B365D'       # TAB Navy
}


def load_polygon_data() -> Optional[dict]:
    """
    Load mineral formation polygon data from GeoJSON file.
    
    Uses manually-digitized formations from published geological references.
    See docs/MINERALS_DATA_SOURCES.md for full citations and methodology.
    
    Returns:
        GeoJSON FeatureCollection dictionary or None if file doesn't exist
    """
    polygon_path = Path(__file__).parent.parent.parent / "data" / "mineral_polygons_v2.json"
    
    if not polygon_path.exists():
        # Fallback to old version if new one doesn't exist
        polygon_path = Path(__file__).parent.parent.parent / "data" / "mineral_polygons.json"
        if not polygon_path.exists():
            return None
    
    try:
        with open(polygon_path, 'r') as f:
            geojson = json.load(f)
        return geojson
    except Exception as e:
        st.warning(f"Could not load polygon data: {e}")
        return None


def create_polygon_layer(geojson_data: dict) -> Optional[pdk.Layer]:
    """
    Create polygon layer for mineral formations with transparent TAB colors.
    
    Displays geological formation boundaries from published sources.
    Tooltip shows formation metadata including citations.
    
    Args:
        geojson_data: GeoJSON FeatureCollection with formation polygons
        
    Returns:
        pydeck PolygonLayer or None if no data
    """
    if not geojson_data or 'features' not in geojson_data:
        return None
    
    features = geojson_data['features']
    if not features:
        return None
    
    # Extract polygon data for pydeck with enriched properties
    polygon_data = []
    for feature in features:
        if feature.get('geometry', {}).get('type') != 'Polygon':
            continue
        
        coordinates = feature['geometry']['coordinates'][0]  # First ring
        properties = feature.get('properties', {})
        
        polygon_data.append({
            'polygon': coordinates,
            'color': properties.get('color', [200, 200, 200, 64]),
            'name': properties.get('name', 'Unknown'),
            'formation_type': properties.get('formation_type', 'Unknown'),
            'minerals': properties.get('minerals', 'Unknown'),
            'status': properties.get('status', 'Unknown'),
            'area_sqkm': properties.get('area_sqkm', 0),
            'counties': properties.get('counties', 'Unknown'),
            'description': properties.get('description', ''),
            'development': properties.get('development', 'No information available'),
            'geological_age': properties.get('geological_age', 'Unknown'),
            'deposit_type': properties.get('deposit_type', 'Unknown'),
            'reserves_estimate': properties.get('reserves_estimate', 'Unknown'),
            'source': properties.get('source', 'See documentation')
        })
    
    if not polygon_data:
        return None
    
    # Create PolygonLayer with transparent fills and white borders
    layer = pdk.Layer(
        "PolygonLayer",
        data=polygon_data,
        get_polygon="polygon",
        get_fill_color="color",
        get_line_color=[255, 255, 255, 200],  # White borders
        line_width_min_pixels=2,
        pickable=True,
        auto_highlight=True,
        opacity=0.35,  # 35% opacity for better visibility while maintaining transparency
        stroked=True,
        filled=True
    )
    
    return layer


def create_minerals_map(df: pd.DataFrame) -> Optional[pdk.Deck]:
    """
    Create professionally designed Texas minerals deposits map.
    
    Design improvements:
    - Smaller, more refined markers (not oversized circles)
    - Subtle borders for better definition
    - Navy blue for Discovery (TAB brand consistency)
    - Soft gold for Exploratory (less harsh than bright yellow)
    - Professional opacity levels for visual hierarchy
    
    Args:
        df: DataFrame with columns: lat, lon, deposit_name, minerals, 
            development_status, estimated_tonnage, county, color, radius
        
    Returns:
        pydeck.Deck object or None if no valid data
    """
    df = df.copy()
    
    # Filter to valid Texas coordinates
    df = df[
        (df['lat'].notna()) & (df['lon'].notna()) &
        (df['lat'] >= 25.8) & (df['lat'] <= 36.5) &
        (df['lon'] >= -106.7) & (df['lon'] <= -93.5)
    ]
    
    if len(df) == 0:
        st.error("No valid deposit coordinates found in Texas bounds")
        return None
    
    # Enhanced tooltip with conditional formatting for both polygons and points
    tooltip = {
        "html": """
        <!-- Formation tooltip (polygon hover) - shows when hovering over shaded regions -->
        {{#name}}
        <div style="font-family: 'Inter', -apple-system, sans-serif; max-width: 450px;">
            <div style="font-weight: 700; font-size: 15px; color: #1B365D; margin-bottom: 6px; border-bottom: 2px solid #C8102E; padding-bottom: 4px;">
                {name}
            </div>
            <div style="font-size: 12px; line-height: 1.5; color: #475569;">
                <div style="margin: 3px 0;"><span style="font-weight: 600; color: #1B365D;">Type:</span> {formation_type}</div>
                <div style="margin: 3px 0;"><span style="font-weight: 600; color: #1B365D;">Minerals:</span> {minerals}</div>
                <div style="margin: 3px 0;"><span style="font-weight: 600; color: #1B365D;">Status:</span> <span style="background-color: #F1F5F9; padding: 2px 8px; border-radius: 3px;">{status}</span></div>
                <div style="margin: 3px 0;"><span style="font-weight: 600; color: #1B365D;">Area:</span> {area_sqkm:,.0f} km²</div>
                <div style="margin: 3px 0;"><span style="font-weight: 600; color: #1B365D;">Counties:</span> {counties}</div>
                <div style="margin: 3px 0;"><span style="font-weight: 600; color: #1B365D;">Age:</span> {geological_age}</div>
                <div style="margin: 6px 0 3px 0; padding-top: 4px; border-top: 1px solid #E2E8F0; font-size: 11px; color: #64748B; line-height: 1.3;">{description}</div>
                <div style="margin: 6px 0 3px 0; padding-top: 4px; border-top: 1px solid #E2E8F0; font-size: 11px; color: #64748B; line-height: 1.3;"><span style="font-weight: 600; color: #1B365D;">Development:</span> {development}</div>
                <div style="margin: 6px 0 0 0; padding-top: 4px; border-top: 1px solid #E2E8F0; font-size: 10px; color: #94A3B8; font-style: italic;"><span style="font-weight: 600;">Source:</span> {source}</div>
            </div>
        </div>
        {{/name}}
        
        <!-- Deposit tooltip (point hover) - shows when hovering over deposit markers -->
        {{#deposit_name}}
        <div style="font-family: 'Inter', -apple-system, sans-serif;">
            <div style="font-weight: 700; font-size: 15px; color: #1B365D; margin-bottom: 6px; border-bottom: 2px solid #C8102E; padding-bottom: 4px;">
                {deposit_name}
            </div>
            <div style="font-size: 13px; line-height: 1.6; color: #475569;">
                <div style="margin: 4px 0;"><span style="font-weight: 600; color: #1B365D;">Minerals:</span> {minerals}</div>
                <div style="margin: 4px 0;"><span style="font-weight: 600; color: #1B365D;">Status:</span> <span style="background-color: #F1F5F9; padding: 2px 8px; border-radius: 3px;">{development_status}</span></div>
                <div style="margin: 4px 0;"><span style="font-weight: 600; color: #1B365D;">Est. Tonnage:</span> {estimated_tonnage:,.0f} MT</div>
                <div style="margin: 4px 0;"><span style="font-weight: 600; color: #1B365D;">County:</span> {county}</div>
            </div>
        </div>
        {{/deposit_name}}
        """,
        "style": {
            "backgroundColor": "#FFFFFF",
            "color": "#0F172A",
            "fontSize": "13px",
            "borderRadius": "8px",
            "padding": "12px 16px",
            "boxShadow": "0 4px 12px rgba(27, 54, 93, 0.15), 0 0 0 1px rgba(27, 54, 93, 0.08)",
            "maxWidth": "480px",
            "border": "none"
        }
    }
    
    # Create refined scatterplot layer with professional styling
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position=["lon", "lat"],
        get_radius="radius",
        get_fill_color="color",
        pickable=True,
        opacity=0.85,
        stroked=True,
        filled=True,
        radius_scale=1,
        radius_min_pixels=8,      # Minimum size: refined, not tiny
        radius_max_pixels=35,     # Maximum size: substantial but not overwhelming
        line_width_min_pixels=1.5,
        line_width_max_pixels=2,
        get_line_color=[255, 255, 255, 200],  # White border for definition
        auto_highlight=True,
        highlight_color=[255, 255, 255, 100]  # Subtle highlight on hover
    )
    
    # Calculate map center
    center_lat = df['lat'].mean()
    center_lon = df['lon'].mean()
    
    # Load polygon overlay data
    layers = []
    polygon_geojson = load_polygon_data()
    if polygon_geojson:
        polygon_layer = create_polygon_layer(polygon_geojson)
        if polygon_layer:
            layers.append(polygon_layer)  # Polygons first (underneath)
    
    # Add point layer on top
    layers.append(layer)
    
    # Create deck with locked Texas viewport (matching Generation tab)
    deck = pdk.Deck(
        layers=layers,
        initial_view_state=pdk.ViewState(
            latitude=31.0,
            longitude=-99.5,
            zoom=4.7,
            pitch=0,
            bearing=0,
            min_zoom=4.7,
            max_zoom=4.7
        ),
        tooltip=tooltip,  # type: ignore
        map_style="mapbox://styles/mapbox/light-v10",
        views=[pdk.View(type='MapView', controller=False)]
    )
    
    return deck


def render_summary_cards(df: pd.DataFrame):
    """
    Display summary statistics cards matching Generation tab style.
    
    Args:
        df: Deposits DataFrame
    """
    col1, col2, col3, col4 = st.columns(4)
    
    total_tonnage = df['estimated_tonnage'].sum()
    major_count = len(df[df['development_status'] == 'Major'])
    counties = df['county'].nunique()
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-card-title">Total Deposits</div>
            <div class="metric-card-value">{len(df):,}</div>
            <div class="metric-card-subtitle">REE & Critical Minerals</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-card-title">Major Development</div>
            <div class="metric-card-value">{major_count}</div>
            <div class="metric-card-subtitle">Active Large-Scale Projects</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-card-title">Est. Total Tonnage</div>
            <div class="metric-card-value">{total_tonnage:,.0f} MT</div>
            <div class="metric-card-subtitle">Combined Mineral Resources</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-card-title">Counties</div>
            <div class="metric-card-value">{counties}</div>
            <div class="metric-card-subtitle">Texas Deposit Locations</div>
        </div>
        """, unsafe_allow_html=True)


def render_status_breakdown(df: pd.DataFrame):
    """
    Display development status breakdown (simplified to match other tabs).
    
    Args:
        df: Deposits DataFrame
    """
    st.subheader("Deposits by Development Status")
    
    status_counts = df['development_status'].value_counts()
    status_tonnage = df.groupby('development_status')['estimated_tonnage'].sum()
    
    # Create a simple dataframe for display
    breakdown_df = pd.DataFrame({
        'Status': status_counts.index,
        'Count': status_counts.values,
        'Tonnage (MT)': status_tonnage.values
    })
    
    # Add percentage column
    total_count = breakdown_df['Count'].sum()
    breakdown_df['Percentage'] = (breakdown_df['Count'] / total_count * 100).round(1)
    
    # Reorder to match standard order
    status_order = ['Major', 'Early', 'Exploratory', 'Discovery']
    breakdown_df['Status'] = pd.Categorical(breakdown_df['Status'], categories=status_order, ordered=True)
    breakdown_df = breakdown_df.sort_values('Status')
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Simple bar chart like Generation tab
        st.bar_chart(breakdown_df.set_index('Status')['Count'])
    
    with col2:
        # Data table with color indicators
        st.dataframe(breakdown_df, hide_index=True)


def render_minerals_legend(df: pd.DataFrame):
    """Display clean legend for mineral deposit status colors (matching Generation tab style)."""
    st.markdown("**Map Legend:**")
    
    status_counts = df['development_status'].value_counts()
    status_tonnage = df.groupby('development_status')['estimated_tonnage'].sum()
    
    # Create color legend in columns
    cols = st.columns(min(4, len(STATUS_COLORS_HEX)))
    
    for i, (status, color_hex) in enumerate(STATUS_COLORS_HEX.items()):
        col_idx = i % len(cols)
        count = status_counts.get(status, 0)
        tonnage = status_tonnage.get(status, 0)
        
        with cols[col_idx]:
            st.markdown(
                f'''
                <div style="display: flex; align-items: center; margin-bottom: 4px;">
                    <div style="width: 12px; height: 12px; background-color: {color_hex}; 
                                border-radius: 50%; margin-right: 8px; border: 1px solid #ddd;"></div>
                    <span style="font-size: 13px;"><b>{status}</b>: {count} deposits ({tonnage:,.0f} MT)</span>
                </div>
                ''', 
                unsafe_allow_html=True
            )
    
    # Check if polygon data is available
    polygon_path = Path(__file__).parent.parent.parent / "data" / "mineral_polygons.json"
    has_polygons = polygon_path.exists()
    
    if has_polygons:
        st.markdown("""
        - �️ **Shaded Regions**: Formation boundaries (USGS MRDS data)  
        - 📍 **Point Markers**: Specific deposit locations  
        - 📏 **Point Size**: Proportional to estimated tonnage (MT)  
        - 🖱️ **Hover**: View detailed deposit information
        """)
    else:
        st.markdown("""
        - �📏 **Point Size**: Proportional to estimated tonnage (MT)  
        - 📍 **Hover**: View detailed deposit information
        """)


def render_deposits_table(df: pd.DataFrame, filters: dict):
    """
    Display filterable table of mineral deposits with professional formatting.
    
    Args:
        df: Deposits DataFrame
        filters: Dictionary of active filters
    """
    st.subheader("Deposit Details")
    
    # Apply filters
    filtered_df = df.copy()
    
    if filters.get('status') and len(filters['status']) > 0:
        filtered_df = filtered_df[filtered_df['development_status'].isin(filters['status'])]
    
    if filters.get('minerals') and len(filters['minerals']) > 0:
        # Filter by any mineral match
        mineral_filter = filtered_df['minerals'].apply(
            lambda x: any(m.strip().lower() in x.lower() for m in filters['minerals'])
        )
        filtered_df = filtered_df[mineral_filter]
    
    # Display count
    st.markdown(f"**Showing {len(filtered_df)} of {len(df)} deposits**")
    
    # Select columns to display
    display_cols = [
        'deposit_name', 'minerals', 'development_status', 
        'estimated_tonnage', 'county', 'details'
    ]
    
    # Rename for display
    display_df = filtered_df[display_cols].copy()
    display_df.columns = [
        'Deposit Name', 'Minerals', 'Status', 
        'Est. Tonnage (MT)', 'County', 'Details'
    ]
    
    # Format tonnage
    display_df['Est. Tonnage (MT)'] = display_df['Est. Tonnage (MT)'].apply(
        lambda x: f"{x:,.0f}" if x > 0 else "TBD"
    )
    
    # Apply professional styling using reusable utility
    styled_df = apply_professional_table_style(display_df.style)
    
    # Display dataframe with professional styling
    st.dataframe(
        styled_df,
        use_container_width=True,
        height=400
    )


def render():
    """Main render function for Minerals & Critical Minerals tab."""
    
    # Minimal header - ultra compact (matching Generation tab)
    st.markdown("### Minerals & Critical Minerals")
    
    # Add advocacy message
    render_advocacy_message('minerals')
    
    # Load data
    try:
        df = load_parquet("minerals_deposits.parquet", "minerals", allow_empty=False)
        
        if df is None or df.empty:
            st.warning(
                "⚠️ No mineral deposit data available. "
                "Run `python etl/mineral_etl.py` to generate data."
            )
            return
        
        # Summary cards
        render_summary_cards(df)
        
        st.markdown("---")
        
        # Filter controls
        st.subheader("Filter Deposits")
        col1, col2 = st.columns(2)
        
        with col1:
            status_options = ['Major', 'Early', 'Exploratory', 'Discovery']
            selected_status = st.multiselect(
                "Development Status",
                options=status_options,
                default=status_options,
                help="Filter deposits by development status"
            )
        
        with col2:
            # Extract unique minerals
            all_minerals = set()
            for minerals_str in df['minerals'].dropna():
                all_minerals.update([m.strip() for m in minerals_str.split(',')])
            
            mineral_options = sorted(list(all_minerals))
            selected_minerals = st.multiselect(
                "Mineral Types",
                options=mineral_options,
                default=[],
                help="Filter by specific minerals"
            )
        
        filters = {
            'status': selected_status,
            'minerals': selected_minerals
        }
        
        # Apply filters to map data
        map_df = df.copy()
        if selected_status:
            map_df = map_df[map_df['development_status'].isin(selected_status)]
        if selected_minerals:
            mineral_filter = map_df['minerals'].apply(
                lambda x: any(m.strip().lower() in x.lower() for m in selected_minerals)
            )
            map_df = map_df[mineral_filter]
        
        st.markdown("---")
        
        # Map section - full width like Generation tab
        st.subheader("Interactive Deposit Map")
        
        if not map_df.empty:
            deck = create_minerals_map(map_df)
            if deck:
                st.pydeck_chart(deck, height=500, use_container_width=True)
            else:
                st.error("Could not create map visualization")
        else:
            st.info("No deposits match the selected filters")
        
        # Data status indicator
        st.success(f"**Live Data**: Texas Mineral Deposits Database - {len(map_df)} deposits from manual curation & geological surveys")
        
        # Enhanced legend with colors
        render_minerals_legend(map_df)
        
        st.markdown("---")
        
        # Status breakdown below map (simplified)
        render_status_breakdown(df)
        
        st.markdown("---")
        
        # Deposits table
        render_deposits_table(df, filters)
        
        # Data Export Section (matching Generation tab)
        st.markdown("---")
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("**Download Mineral Deposits Data**")
        with col2:
            create_download_button(
                df=df[['deposit_name', 'minerals', 'development_status', 'estimated_tonnage', 
                       'county', 'lat', 'lon', 'details']],
                filename_prefix="texas_mineral_deposits",
                label="Download Deposits Data"
            )
        
        # Data source footer
        last_updated = get_last_updated(df)
        render_data_source_footer("minerals", last_updated)
        
        # TODO section for manual updates
        with st.expander("📝 Manual Data Update Instructions"):
            st.markdown(
                """
                **To add or update mineral deposits:**
                
                1. Edit `data/manual_mineral_deposits.csv` with new deposit information
                2. Run the ETL script: `python etl/mineral_etl.py`
                3. Refresh this dashboard to see updated data
                
                **Required CSV columns:**
                - `deposit_name`: Name of the deposit/site
                - `lat`: Latitude (decimal degrees)
                - `lon`: Longitude (decimal degrees)
                - `minerals`: Comma-separated list of minerals
                - `estimated_tonnage`: Estimated tonnage in metric tons (or 0 for TBD)
                - `development_status`: Major, Early, Exploratory, or Discovery
                - `county`: Texas county name
                - `details`: Additional notes and description
                
                **Development Status Definitions:**
                - **Major**: Active large-scale development (e.g., Round Top Mountain, Smackover Formation)
                - **Early**: Initial production or facility operations (e.g., Zinc, Helium plants)
                - **Exploratory**: Geological surveys and feasibility studies
                - **Discovery**: Initial prospecting and identification
                
                **For GeoJSON/Shapefile Data:**
                TODO: Implement GeoJSON loading in `etl/mineral_etl.py` when shapefile sources become available.
                Place GeoJSON files in `data/mineral_deposits.geojson` and update the ETL script.
                """
            )
        
    except Exception as e:
        st.error(f"Error loading mineral deposit data: {e}")
        st.info(
            "If you haven't generated the data yet, run: `python etl/mineral_etl.py`"
        )


if __name__ == "__main__":
    render()
