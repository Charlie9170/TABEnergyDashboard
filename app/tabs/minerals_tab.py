"""
Minerals & Critical Minerals Tab - Texas REE and Critical Mineral Deposits

Displays Texas Rare Earth Elements (REEs) and Critical Minerals deposits
with development status classification and geographic visualization.
"""

import streamlit as st
import pandas as pd
import pydeck as pdk
import math
from pathlib import Path
from typing import Optional

import sys
sys.path.append(str(Path(__file__).parent.parent))

from utils.loaders import load_parquet, get_last_updated, get_file_modification_time
from utils.data_sources import render_data_source_footer
from utils.colors import TAB_COLORS, NEUTRAL_COLORS
from utils.export import create_download_button


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
    
    # Enhanced tooltip with professional styling
    tooltip = {
        "html": """
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
        """,
        "style": {
            "backgroundColor": "#FFFFFF",
            "color": "#0F172A",
            "fontSize": "13px",
            "borderRadius": "8px",
            "padding": "12px 16px",
            "boxShadow": "0 4px 12px rgba(27, 54, 93, 0.15), 0 0 0 1px rgba(27, 54, 93, 0.08)",
            "maxWidth": "340px",
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
    
    # Create deck with refined Texas view
    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=pdk.ViewState(
            latitude=center_lat,
            longitude=center_lon,
            zoom=5.8,              # Slightly more zoomed in for better detail
            pitch=0,
            bearing=0,
            min_zoom=4.5,
            max_zoom=10
        ),
        tooltip=tooltip,  # type: ignore
        map_style="mapbox://styles/mapbox/light-v10"
    )
    
    return deck


def render_summary_cards(df: pd.DataFrame):
    """
    Display summary statistics cards at the top of the tab.
    
    Args:
        df: Deposits DataFrame
    """
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Total Deposits",
            value=f"{len(df):,}",
            help="Total number of mineral deposits tracked"
        )
    
    with col2:
        major_count = len(df[df['development_status'] == 'Major'])
        st.metric(
            label="Major Development",
            value=f"{major_count}",
            help="Deposits in active major development"
        )
    
    with col3:
        total_tonnage = df['estimated_tonnage'].sum()
        st.metric(
            label="Est. Total Tonnage",
            value=f"{total_tonnage:,.0f} MT",
            help="Total estimated mineral tonnage (metric tons)"
        )
    
    with col4:
        counties = df['county'].nunique()
        st.metric(
            label="Counties",
            value=f"{counties}",
            help="Number of Texas counties with deposits"
        )


def render_status_breakdown(df: pd.DataFrame):
    """
    Display refined development status breakdown with professional design.
    
    Args:
        df: Deposits DataFrame
    """
    st.markdown("### Development Status Breakdown")
    
    status_counts = df['development_status'].value_counts().sort_index()
    status_tonnage = df.groupby('development_status')['estimated_tonnage'].sum()
    
    # Create columns for status breakdown
    cols = st.columns(4)
    
    for idx, (status, color) in enumerate(STATUS_COLORS_HEX.items()):
        with cols[idx]:
            count = status_counts.get(status, 0)
            tonnage = status_tonnage.get(status, 0)
            
            # Professional card design with refined styling
            st.markdown(
                f"""
                <div style="
                    padding: 18px;
                    border-radius: 10px;
                    border-left: 5px solid {color};
                    background: linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%);
                    margin-bottom: 10px;
                    box-shadow: 0 2px 8px rgba(27, 54, 93, 0.08);
                    transition: transform 0.2s ease;
                ">
                    <div style="
                        font-weight: 600; 
                        color: #64748B; 
                        font-size: 12px; 
                        text-transform: uppercase;
                        letter-spacing: 0.5px;
                        margin-bottom: 8px;
                    ">
                        {status}
                    </div>
                    <div style="
                        font-size: 32px; 
                        font-weight: 700; 
                        color: {color};
                        line-height: 1;
                        margin-bottom: 8px;
                    ">
                        {count}
                    </div>
                    <div style="
                        font-size: 13px; 
                        color: #64748B;
                        font-weight: 500;
                    ">
                        {tonnage:,.0f} MT
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )


def render_minerals_legend():
    """Display refined legend for mineral deposit status colors."""
    st.markdown("### Map Legend")
    
    legend_html = """
    <div style='
        padding: 16px; 
        background: linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%); 
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(27, 54, 93, 0.08);
        border: 1px solid #E2E8F0;
    '>
    """
    
    for status, color_hex in STATUS_COLORS_HEX.items():
        legend_html += f"""
        <div style='margin: 10px 0; display: flex; align-items: center;'>
            <div style='
                width: 14px; 
                height: 14px; 
                background-color: {color_hex}; 
                border-radius: 50%; 
                margin-right: 12px;
                border: 2px solid rgba(255, 255, 255, 0.9);
                box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15);
            '></div>
            <span style='color: #1B365D; font-weight: 600; font-size: 13px;'>{status}</span>
        </div>
        """
    
    legend_html += """
    <div style='
        margin-top: 14px; 
        padding-top: 12px; 
        border-top: 1px solid #E2E8F0;
        font-size: 11px;
        color: #64748B;
        line-height: 1.5;
    '>
        <div><strong>Marker size</strong> indicates estimated tonnage</div>
        <div style='margin-top: 4px;'><strong>Hover</strong> for deposit details</div>
    </div>
    </div>
    """
    
    st.markdown(legend_html, unsafe_allow_html=True)


def render_deposits_table(df: pd.DataFrame, filters: dict):
    """
    Display filterable table of mineral deposits.
    
    Args:
        df: Deposits DataFrame
        filters: Dictionary of active filters
    """
    st.markdown("### Deposit Details")
    
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
    
    # Display dataframe with styling
    st.dataframe(
        display_df,
        use_container_width=True,
        height=400
    )


def render():
    """Main render function for Minerals & Critical Minerals tab."""
    
    # Tab header
    st.markdown(
        """
        <div style="padding: 20px 0; border-bottom: 2px solid #C8102E; margin-bottom: 30px;">
            <h1 style="color: #1B365D; margin: 0; font-size: 32px; font-weight: 700;">
                Minerals & Critical Minerals
            </h1>
            <p style="color: #64748B; margin: 8px 0 0 0; font-size: 16px;">
                Texas Rare Earth Elements (REEs) & Critical Minerals Development
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
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
        
        # Status breakdown
        render_status_breakdown(df)
        
        st.markdown("---")
        
        # Filter controls
        st.markdown("### Filters")
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
        
        # Map section
        col_map, col_legend = st.columns([3, 1])
        
        with col_map:
            st.markdown("### Deposit Locations")
            
            if not map_df.empty:
                deck = create_minerals_map(map_df)
                if deck:
                    st.pydeck_chart(deck)
                else:
                    st.error("Could not create map visualization")
            else:
                st.info("No deposits match the selected filters")
        
        with col_legend:
            render_minerals_legend()
        
        st.markdown("---")
        
        # Deposits table
        render_deposits_table(df, filters)
        
        st.markdown("---")
        
        # Export functionality
        st.markdown("### Export Data")
        create_download_button(
            df[['deposit_name', 'minerals', 'development_status', 'estimated_tonnage', 
                'county', 'lat', 'lon', 'details']],
            filename_prefix="texas_mineral_deposits",
            label="Download Deposits Data (CSV)"
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
