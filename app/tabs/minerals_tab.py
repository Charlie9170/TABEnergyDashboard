"""
Minerals & Critical Minerals Tab - Texas REE and Critical Mineral Deposits

Displays Texas Rare Earth Elements (REEs) and Critical Minerals deposits
with development status classification and geographic visualization.
"""

import streamlit as st
import pandas as pd
import pydeck as pdk
import json
import logging
from pathlib import Path
from typing import Optional

import sys
sys.path.append(str(Path(__file__).parent.parent))

from utils.loaders import load_parquet, get_last_updated
from utils.data_sources import format_ct, render_data_source_footer
from utils.export import create_download_button
from utils.table_styling import apply_professional_table_style

logger = logging.getLogger(__name__)


# Development status color palette (TAB blue gradient - red to blues)
STATUS_COLORS = {
    'Major': [220, 38, 38, 180],        # Natural Gas Red #DC2626
    'Discovery': [27, 54, 93, 180],     # Wind Navy Blue #1B365D (darkest blue)
    'Early': [71, 85, 105, 180],        # Slate-700 #475569 (medium blue-gray)
    'Exploratory': [100, 116, 139, 180], # Battery Slate #64748B (light blue-gray)
}

STATUS_COLORS_HEX = {
    'Major': '#DC2626',          # Natural Gas Red
    'Discovery': '#1B365D',      # Wind Navy (darkest blue)
    'Early': '#475569',          # Slate-700 (medium blue-gray)
    'Exploratory': '#64748B',    # Battery Slate (light blue-gray)
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
    except Exception:
        logger.exception("Minerals tab: unable to read polygon overlay %s", polygon_path)
        st.warning("Formation overlays are temporarily unavailable.")
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
        get_fill_color="color",  # Use TAB brand colors from GeoJSON (red/navy/gray by status)
        get_line_color=[255, 255, 255, 255],  # SOLID white borders
        line_width_min_pixels=3,  # THICK
        pickable=True,
        auto_highlight=True,
        opacity=0.65,  # 65% opacity - FORMATIONS PRIMARY for better visibility while maintaining transparency
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
    
    # Compact tooltip for formations (no conditionals, compressed width)
    tooltip = {
        "html": """
        <div style="font-family: 'Inter', -apple-system, sans-serif; max-width: 320px;">
            <div style="font-weight: 700; font-size: 14px; color: #1B365D; margin-bottom: 4px; border-bottom: 2px solid #DC2626; padding-bottom: 3px;">
                {name}
            </div>
            <div style="font-size: 11px; line-height: 1.4; color: #475569;">
                <div style="margin: 2px 0;"><span style="font-weight: 600; color: #1B365D;">Type:</span> {formation_type}</div>
                <div style="margin: 2px 0;"><span style="font-weight: 600; color: #1B365D;">Minerals:</span> {minerals}</div>
                <div style="margin: 2px 0;"><span style="font-weight: 600; color: #1B365D;">Status:</span> <span style="background-color: #F1F5F9; padding: 1px 6px; border-radius: 3px; font-size: 10px;">{status}</span></div>
                <div style="margin: 2px 0;"><span style="font-weight: 600; color: #1B365D;">Area:</span> {area_sqkm} km²</div>
                <div style="margin: 2px 0;"><span style="font-weight: 600; color: #1B365D;">Counties:</span> {counties}</div>
                <div style="margin: 4px 0 2px 0; padding-top: 3px; border-top: 1px solid #E2E8F0; font-size: 10px; color: #64748B; line-height: 1.3;">{description}</div>
                <div style="margin: 2px 0 0 0; padding-top: 3px; font-size: 9px; color: #94A3B8; font-style: italic;"><span style="font-weight: 600;">Source:</span> {source}</div>
            </div>
        </div>
        """,
        "style": {
            "backgroundColor": "#FFFFFF",
            "color": "#0F172A",
            "fontSize": "12px",
            "borderRadius": "6px",
            "padding": "10px 12px",
            "boxShadow": "0 4px 12px rgba(27, 54, 93, 0.15), 0 0 0 1px rgba(27, 54, 93, 0.08)",
            "maxWidth": "340px",
            "border": "none"
        }
    }
    
    # Create refined scatterplot layer with professional styling
    point_layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position=["lon", "lat"],
        get_radius="radius",
        get_fill_color=[120, 120, 120, 80],  # GRAY
        pickable=True,
        opacity=0.25,  # Very subtle
        stroked=True,
        filled=True,
        radius_scale=1,
        radius_min_pixels=3,      # Minimum size: refined, not tiny
        radius_max_pixels=8,     # Maximum size: substantial but not overwhelming
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
    layers.append(point_layer)
    
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
    """Horizontal legend matching Generation tab style - clean, professional, no emojis."""
    
    # Get formation status data (using development_status for deposits)
    status_counts = df['development_status'].value_counts()
    
    # Build horizontal legend HTML matching Generation/Fuel Mix style
    legend_items = []
    for status in ['Major', 'Discovery', 'Early', 'Exploratory']:  # Consistent order
        count = status_counts.get(status, 0)
        color = STATUS_COLORS_HEX.get(status, '#CCCCCC')
        
        legend_items.append(
            f'<span style="margin-right: 20px; white-space: nowrap;">'
            f'<span style="display: inline-block; width: 12px; height: 12px; '
            f'background-color: {color}; margin-right: 6px; vertical-align: middle; '
            f'border-radius: 50%; border: 1px solid rgba(0,0,0,0.15);"></span>'
            f'<span style="font-size: 12px; color: #374151;"><b>{status}</b> ({count} formations)</span>'
            f'</span>'
        )
    
    # Render horizontal legend bar
    st.markdown(
        f'<div style="text-align: center; padding: 12px 0; background-color: #f9fafb; '
        f'border-top: 1px solid #e5e7eb; border-bottom: 1px solid #e5e7eb; margin: 16px 0;">'
        f'{"".join(legend_items)}'
        f'</div>',
        unsafe_allow_html=True
    )
    
    # Simple interaction instructions (no emojis)
    st.markdown(
        '<div style="text-align: center; font-size: 11px; color: #6b7280; margin-top: 8px;">'
        'Hover over formations for details • Click and drag to pan • Scroll to zoom'
        '</div>',
        unsafe_allow_html=True
    )



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
    st.subheader(
        "Minerals & Critical Minerals",
        help="Manually compiled Texas deposits from public geological surveys and industry disclosures.",
    )
    
    # Add advocacy message (custom HTML matching Generation tab style)
    st.markdown("""
    <div style="padding: 8px 12px; background-color: #f8f9fa; border-left: 3px solid #1f4788; 
                margin: 12px 0 8px 0; font-size: 14px; color: #4b5563; line-height: 1.5;">
        <strong>TAB Policy:</strong> Texas Association of Business supports responsible development of Texas' mineral resources to strengthen supply chain security and energy infrastructure.
    </div>
    """, unsafe_allow_html=True)
    
    # Load data
    try:
        df = load_parquet("minerals_deposits.parquet", "minerals", allow_empty=False)
        
        if df is None or df.empty:
            st.warning("Mineral deposit data is not available.")
            return
        
        # Summary cards
        render_summary_cards(df)
        
        map_df = df.copy()
        st.subheader("Deposit Map")
        
        if not map_df.empty:
            deck = create_minerals_map(map_df)
            if deck:
                st.pydeck_chart(deck, height=500, use_container_width=True)
            else:
                st.error("Could not create map visualization")
        else:
            st.info("No deposits match the selected filters")
        
        render_minerals_legend(map_df)
        st.info(
            "**Manually compiled Texas mineral deposits** from public geological surveys "
            "and industry disclosures. "
            f"Last refreshed: {format_ct(get_last_updated(df))}."
        )
        
        st.markdown("---")
        
        # Filters section (directly under legend/key)
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
        
        st.markdown("---")
        
        # Deposits table
        render_deposits_table(df, filters)
        
        with st.expander("Methodology"):
            st.markdown(
                """
                This dataset is a **manual compilation** of publicly disclosed Texas deposits.
                It is not an automated EIA or ERCOT feed and should not be treated as complete
                or current to a fixed reporting period.

                **Development status**
                - **Major**: Active large-scale development
                - **Early**: Initial production or facility operations
                - **Exploratory**: Geological surveys and feasibility studies
                - **Discovery**: Initial prospecting and identification
                """
            )

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
        
        render_data_source_footer("minerals", get_last_updated(df))
        
    except Exception:
        logger.exception("Minerals tab: unexpected error")
        st.error("Error loading mineral deposit data.")


if __name__ == "__main__":
    render()
