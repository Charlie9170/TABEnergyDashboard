"""
Interconnection Queue Tab - ERCOT Planned Generation Projects

Fixed implementation with proper coordinate validation, logarithmic scaling,
and TAB color scheme for production-ready visualization.
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
from utils.colors import get_fuel_color_hex, FUEL_COLORS_HEX
from utils.export import create_download_button


def create_queue_map(df: pd.DataFrame) -> Optional[pdk.Deck]:
    """
    Create Texas-focused interconnection queue map with proper scaling.
    Uses TAB color scheme with red for large projects, navy for small.
    
    Args:
        df: DataFrame with columns: lat, lon, capacity_mw, project_name, fuel_type, county, interconnection_status
        
    Returns:
        pydeck.Deck object or None if no valid data
    """
    df = df.copy()
    
    # CRITICAL FIX #1: Filter to valid Texas coordinates only
    df = df[
        (df['lat'].notna()) & (df['lon'].notna()) &
        (df['lat'] >= 25.8) & (df['lat'] <= 36.5) &
        (df['lon'] >= -106.7) & (df['lon'] <= -93.5)
    ]
    
    if len(df) == 0:
        st.error("No valid project coordinates found in Texas bounds")
        return None
    
    # CRITICAL FIX #2: Proper logarithmic radius scaling
    max_capacity = df['capacity_mw'].max()
    min_capacity = df['capacity_mw'].min()
    
    def proper_radius_scaling(capacity):
        """
        Logarithmic scaling so size differences are actually visible.
        Small projects: 6-10px
        Medium projects: 10-20px
        Large projects: 20-40px
        """
        if max_capacity == min_capacity:
            return 15
        
        # Normalize to 0-1
        normalized = (capacity - min_capacity) / (max_capacity - min_capacity)
        
        # Logarithmic scaling for better visual separation
        log_scaled = math.log(1 + normalized * 9) / math.log(10)  # 0-1 range
        
        # Map to pixel range: 6-40px
        return 6 + (log_scaled * 34)
    
    df['radius'] = df['capacity_mw'].apply(proper_radius_scaling)
    
    # CRITICAL FIX #3: TAB color scheme (Red for large, Navy for small) - NOT GREEN!
    def get_project_color(capacity):
        """
        Color by size: Large projects = TAB Red, Small = TAB Navy
        Creates visual hierarchy
        """
        normalized = (capacity - min_capacity) / (max_capacity - min_capacity)
        
        if normalized > 0.7:  # Top 30% - TAB Red
            return [200, 16, 46, 200]  # TAB Red
        elif normalized > 0.4:  # Middle - Dark Red
            return [160, 16, 46, 180]
        else:  # Bottom 40% - TAB Navy
            return [27, 54, 93, 160]  # TAB Navy
    
    df['color'] = df['capacity_mw'].apply(get_project_color)
    
    # CRITICAL FIX #4: Enhanced tooltip with project details
    tooltip = {
        "html": """
        <b>{project_name}</b><br/>
        <b>Capacity:</b> {capacity_mw} MW<br/>
        <b>Fuel:</b> {fuel_type}<br/>
        <b>County:</b> {county}<br/>
        <b>Status:</b> {interconnection_status}
        """,
        "style": {
            "backgroundColor": "white",
            "color": "#1B365D",
            "fontSize": "13px",
            "borderRadius": "6px",
            "padding": "10px",
            "boxShadow": "0 2px 8px rgba(0,0,0,0.2)"
        }
    }
    
    # Create scatterplot layer with white outlines
    layer = pdk.Layer(
        'ScatterplotLayer',
        df,
        get_position=['lon', 'lat'],
        get_color='color',
        get_radius='radius',
        radius_scale=1,
        radius_min_pixels=4,
        radius_max_pixels=50,
        pickable=True,
        auto_highlight=True,
        get_line_color=[255, 255, 255, 180],  # White outline for visibility
        stroked=True,
        filled=True,
        line_width_min_pixels=1,
        opacity=0.85
    )
    
    # CRITICAL FIX #5: Better viewport - centered on West Texas where projects cluster
    # Most queue projects are in Panhandle (wind) around 33.5°N, -101°W
    view_state = pdk.ViewState(
        latitude=31.5,       # Slightly south to show full Texas
        longitude=-100.0,    # Centered on West Texas wind corridor
        zoom=5.2,            # More zoomed in than other tabs
        pitch=0,
        min_zoom=4.5,
        max_zoom=7.0,        # Allow zoom for detailed inspection
    )
    
    # CRITICAL FIX: Remove tooltip from pdk.Deck (type error) - handled by st.pydeck_chart instead
    return pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_style='mapbox://styles/mapbox/light-v10',
        views=[pdk.View(type='MapView', controller=True)]  # Enable pan/zoom for queue
    )


def render():
    """Render the Interconnection Queue tab with comprehensive error handling."""
    
    # Header
    st.markdown("### ERCOT Interconnection Queue")
    st.markdown("Real projects from ERCOT's Capacity, Demand and Reserves (CDR) Report showing the interconnection queue pipeline of future generation capacity.")
    
    try:
        # Load queue data
        data_path = Path(__file__).parent.parent.parent / "data" / "queue.parquet"
        
        # Check if file exists
        if not data_path.exists():
            st.warning("⚠️ **Interconnection queue data not available**")
            st.info("Run the ETL script to fetch ERCOT queue data.")
            st.code("python etl/ercot_queue_etl.py", language="bash")
            return
        
        df = pd.read_parquet(data_path)
        
        # Check if data is empty
        if len(df) == 0:
            st.warning("⚠️ **No projects in queue**")
            st.info("🔄 The data file is empty. Re-run the ETL script.")
            st.code("python etl/ercot_queue_etl.py", language="bash")
            return
        
        # Validate and filter to Texas coordinates
        df_valid = df[
            (df['lat'].notna()) & (df['lon'].notna()) &
            (df['lat'] >= 25.8) & (df['lat'] <= 36.5) &
            (df['lon'] >= -106.7) & (df['lon'] <= -93.5)
        ].copy()
        
        if len(df_valid) == 0:
            st.error("❌ **No projects with valid Texas coordinates found**")
            st.info("Check the ETL script coordinate validation.")
            return
        
        # Ensure required columns exist
        required_cols = ['capacity_mw', 'project_name', 'fuel_type']
        missing_cols = [col for col in required_cols if col not in df_valid.columns]
        if missing_cols:
            st.error(f"❌ **Missing required columns**: {missing_cols}")
            return
    
        # Summary metrics
        total_capacity = df_valid['capacity_mw'].sum()
        total_projects = len(df_valid)
        fuel_types = df_valid['fuel_type'].nunique()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-card-title">Total Planned Capacity</div>
                <div class="metric-card-value">{total_capacity:,.0f} MW</div>
                <div class="metric-card-subtitle">Pipeline Projects</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-card-title">Projects in Queue</div>
                <div class="metric-card-value">{total_projects}</div>
                <div class="metric-card-subtitle">Awaiting Interconnection</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-card-title">Fuel Types</div>
                <div class="metric-card-value">{fuel_types}</div>
                <div class="metric-card-subtitle">Generation Technologies</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("")  # Spacing
    
        # Map section
        st.subheader("Project Locations")
        
        deck = create_queue_map(df_valid)
        if deck is None:
            st.error("❌ **Unable to create map** - No valid coordinates found")
            return
            
        st.pydeck_chart(deck, height=600, use_container_width=True)
        
        # Status indicator
        timestamp = get_file_modification_time("queue.parquet")
        st.success(f"**ERCOT CDR Data** - Last Updated: {timestamp}")
        
        # UPDATED LEGEND - matches new color scheme
        st.markdown("### Map Legend")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            <div style="display: flex; align-items: center; gap: 8px;">
                <div style="width: 20px; height: 20px; background-color: rgb(200, 16, 46); border-radius: 50%; border: 2px solid white;"></div>
                <span><b>Large Projects</b> (>70th percentile)</span>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div style="display: flex; align-items: center; gap: 8px;">
                <div style="width: 16px; height: 16px; background-color: rgb(160, 16, 46); border-radius: 50%; border: 2px solid white;"></div>
                <span><b>Medium Projects</b> (40-70th percentile)</span>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div style="display: flex; align-items: center; gap: 8px;">
                <div style="width: 12px; height: 12px; background-color: rgb(27, 54, 93); border-radius: 50%; border: 2px solid white;"></div>
                <span><b>Small Projects</b> (<40th percentile)</span>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("""
        - **Dot Size**: Proportional to project capacity (MW) using logarithmic scaling
        - **Hover**: View detailed project information
        - **Pan/Zoom**: Enabled for detailed inspection
        """)
        
        st.markdown("---")
    
        # Data export
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("**Download Queue Data for Policy Analysis**")
        with col2:
            create_download_button(
                df=df_valid,
                filename_prefix="interconnection_queue",
                label="Download Queue Data"
            )
        
        # Project breakdown by fuel type
        st.subheader("Queue Composition by Technology")
        
        fuel_summary = df_valid.groupby('fuel_type').agg({
            'capacity_mw': 'sum',
            'project_name': 'count'
        }).round(0).sort_values('capacity_mw', ascending=False)
        
        fuel_summary.columns = ['Total Capacity (MW)', 'Number of Projects']
        fuel_summary['Avg Size (MW)'] = (fuel_summary['Total Capacity (MW)'] / fuel_summary['Number of Projects']).round(0)
        
        st.dataframe(fuel_summary, use_container_width=True)
        
        # Key insights
        st.subheader("Key Insights")
        
        dominant_fuel = fuel_summary.index[0]
        dominant_capacity = fuel_summary.iloc[0]['Total Capacity (MW)']
        dominant_pct = (dominant_capacity / total_capacity) * 100
        
        avg_project_size = df_valid['capacity_mw'].mean()
        largest_project = df_valid.loc[df_valid['capacity_mw'].idxmax()]
        
        st.markdown(f"""
        - **Pipeline Scale**: {total_projects:,} projects representing {total_capacity:,.0f} MW of future capacity
        - **Dominant Technology**: {dominant_fuel} accounts for {dominant_pct:.1f}% of planned capacity
        - **Average Project Size**: {avg_project_size:.0f} MW per project
        - **Largest Project**: {largest_project['project_name']} ({largest_project['capacity_mw']:.0f} MW)
        - **Geographic Concentration**: Most projects located in West Texas (Panhandle wind corridor)
        - **Data Source**: ERCOT Capacity, Demand and Reserves (CDR) Report
        """)
        
        # Technical notes
        with st.expander("Technical Notes"):
            st.markdown(f"""
            **Data Source:**
            - Source: ERCOT CDR (Capacity, Demand and Reserves) Report
            - Update Frequency: Monthly
            - Coverage: All projects in ERCOT interconnection queue
            - Last Updated: {timestamp}
            
            **Map Features:**
            - Color coding by project size (red = large, navy = small)
            - Logarithmic radius scaling for visual clarity
            - Centered on West Texas where most projects located
            - Interactive pan/zoom enabled for detailed inspection
            - White outlines for visibility on light background
            
            **Data Processing:**
            - Coordinates validated to Texas bounds (25.8-36.5°N, -106.7 to -93.5°W)
            - Invalid coordinates filtered out
            - Project capacities range from {df_valid['capacity_mw'].min():.0f} to {df_valid['capacity_mw'].max():.0f} MW
            - {len(df_valid)} of {len(df)} projects have valid Texas coordinates
            """)
        
        # Render footer
        last_updated = get_last_updated(df_valid)
        render_data_source_footer('queue', last_updated)
        
    except KeyError as e:
        st.error(f"❌ **Data Format Error**: Missing required column: {str(e)}")
        st.info("🔄 The data file may be corrupted. Try re-running the ETL script.")
        st.code("python etl/ercot_queue_etl.py", language="bash")
        
    except pd.errors.ParserError:
        st.error(f"❌ **File Corrupted**: Unable to read queue data")
        st.info("🔄 The parquet file may be damaged. Re-run the ETL script.")
        st.code("python etl/ercot_queue_etl.py", language="bash")
        
    except Exception as e:
        st.error(f"❌ **Unexpected error loading queue data**: {str(e)}")
        st.info("🔄 Try refreshing the page. If the issue persists, re-run the ETL script.")
        st.code("python etl/ercot_queue_etl.py", language="bash")