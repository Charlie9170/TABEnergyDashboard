"""
Interconnection Queue Tab - ERCOT Planned Generation Projects

Fixed implementation with proper coordinate validation, logarithmic scaling,
and TAB color scheme for production-ready visualization.
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
from utils.colors import get_fuel_color_hex, FUEL_COLORS_HEX
from utils.export import create_download_button
from utils.advocacy import render_advocacy_message

# Default view = projects with a signed interconnection agreement (SGIA / IA).
# ERCOT Planning Guide §5.1.1: a "large generator" is ≥10 MW; GIS already splits
# Large vs Small Gen on that line. Texas SB6 / 16 TAC §25.194's 75 MW threshold
# applies to large *loads* (Batch Zero), not generator interconnection.
# IA signed is a study-process milestone, not a guarantee of construction.
COMMITTED_STATUS = "Interconnection Agreement Signed"


def texas_mappable_mask(df: pd.DataFrame) -> pd.Series:
    """Rows with coordinates inside Texas bounds (map-only filter)."""
    return (
        df['lat'].notna() & df['lon'].notna() &
        (df['lat'] >= 25.8) & (df['lat'] <= 36.5) &
        (df['lon'] >= -106.7) & (df['lon'] <= -93.5)
    )


def select_queue_view(df: pd.DataFrame, show_full_queue: bool) -> pd.DataFrame:
    """Headline/table set. Default: signed IA. Full toggle: every parsed row."""
    if show_full_queue:
        return df.copy()
    return df[df['status'] == COMMITTED_STATUS].copy()


def gis_public_vs_summary_caption(parsed_rows: int) -> Optional[str]:
    """One-line coverage note: public detail-sheet rows vs Summary-sheet total."""
    meta_path = Path(__file__).parent.parent.parent / "data" / "queue_gis_metadata.json"
    if not meta_path.exists():
        return None
    try:
        meta = json.loads(meta_path.read_text())
        source_n = int(meta["source_total_interconnection_requests"])
        public_n = int(meta.get("parsed_public_detail_rows", parsed_rows))
    except (OSError, KeyError, TypeError, ValueError):
        return None
    withheld = max(source_n - public_n, 0)
    return (
        f"Public GIS detail sheets (Large Gen + Small Gen): **{public_n:,}** projects. "
        f"ERCOT's Summary sheet reports **{source_n:,}** total interconnection requests. "
        f"The other {withheld:,} are withheld from those public sheets "
        f"(pre-FIS large generators and not-yet-model-ready small generators)."
    )


def create_queue_map(df: pd.DataFrame) -> Optional[pdk.Deck]:
    """
    Create Texas-focused interconnection queue map with proper scaling.
    Uses TAB color scheme with red for large projects, navy for small.
    
    Args:
        df: DataFrame with columns: lat, lon, proposed_mw, project_name, fuel, county, status
        
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
    
    # CRITICAL FIX #2: Percentile-based radius scaling for visual differentiation
    max_capacity = df['proposed_mw'].max()
    min_capacity = df['proposed_mw'].min()
    
    def percentile_radius_scaling(capacity):
        """
        Scale radius based on capacity percentiles for clear size differences:
        - Bottom 33%: Small dots (8-12px)
        - Middle 33%: Medium dots (12-18px)  
        - Top 33%: Large dots (18-30px)
        Uses square root scaling within each tier for smooth transitions.
        """
        if max_capacity == min_capacity:
            return 15
        
        # Normalize to 0-1
        normalized = (capacity - min_capacity) / (max_capacity - min_capacity)
        
        # Square root scaling for better visual separation
        sqrt_scaled = math.sqrt(normalized)
        
        # Map to pixel range: 8-30px with clear size differences
        return 8 + (sqrt_scaled * 22)
    
    df['radius'] = df['proposed_mw'].apply(percentile_radius_scaling)
    
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
    
    df['color'] = df['proposed_mw'].apply(get_project_color)
    
    # CRITICAL FIX #4: Enhanced tooltip with project name (like generation map)
    tooltip = {
        "html": "<b>{project_name}</b><br/>Capacity: {proposed_mw} MW<br/>Fuel: {fuel}<br/>County: {county}",
        "style": {
            "backgroundColor": "white",
            "color": "black",
            "fontSize": "14px",
            "borderRadius": "6px",
            "padding": "8px 12px",
            "boxShadow": "0 2px 8px rgba(0,0,0,0.15)"
        }
    }
    
    # Create scatterplot layer with white outlines and hover support
    layer = pdk.Layer(
        'ScatterplotLayer',
        df,
        get_position=['lon', 'lat'],
        get_color='color',
        get_radius='radius',
        radius_scale=1,
        radius_min_pixels=6,        # Slightly larger min for visibility
        radius_max_pixels=45,       # Slightly smaller max for proportion
        pickable=True,
        auto_highlight=True,
        get_line_color=[255, 255, 255, 180],  # White outline for visibility
        stroked=True,
        filled=True,
        line_width_min_pixels=1,
        line_width_max_pixels=2,
        opacity=0.8
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
    
    # Return deck with tooltip (like generation map)
    return pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_style='mapbox://styles/mapbox/light-v10',
        tooltip=tooltip,  # type: ignore
        views=[pdk.View(type='MapView', controller=True)]  # Enable pan/zoom for queue
    )


def render():
    """Render the Interconnection Queue tab with comprehensive error handling."""
    
    # Header
    st.markdown("### ERCOT Interconnection Queue")
    st.markdown("Projects from ERCOT's Generator Interconnection Status (GIS) Report — the actual interconnection queue, republished monthly.")

    # Compact advocacy message - single line, non-intrusive
    st.markdown("""
    <div style="padding: 8px 12px; background-color: #f8f9fa; border-left: 3px solid #1f4788; 
                margin: 12px 0 20px 0; font-size: 14px; color: #4b5563; line-height: 1.5;">
        <strong>TAB Policy:</strong> Texas Association of Business advocates for efficient interconnection 
        processes and grid infrastructure to support new generation projects.
    </div>
    """, unsafe_allow_html=True)
    
    try:
        # Load queue data via the canonical loader — provides schema
        # normalization, type coercion, validation, and graceful
        # degradation consistent with every other tab (previously this
        # tab bypassed load_parquet() with a raw pd.read_parquet() call).
        df = load_parquet("queue.parquet", "queue", allow_empty=True)

        coverage = gis_public_vs_summary_caption(len(df))
        if coverage:
            st.caption(coverage)

        # Check if data is empty
        if len(df) == 0:
            st.warning("⚠️ **No projects in queue**")
            st.info("🔄 The data file is empty. Re-run the ETL script.")
            st.code("python etl/ercot_gis_queue_etl.py", language="bash")
            return

        # Headline metrics use the complete parsed queue (or IA-signed subset).
        # Coordinate filtering is map-only — do not silently drop rows from totals.
        required_cols = ['proposed_mw', 'project_name', 'fuel', 'status']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            st.error(f"❌ **Missing required columns**: {missing_cols}")
            return

        show_full_queue = st.toggle(
            "Show full public queue (includes projects still under study)",
            value=False,
        )

        df_view = select_queue_view(df, show_full_queue)
        df_map = df_view[texas_mappable_mask(df_view)].copy()

        st.caption(
            "Default: projects with a signed interconnection agreement (SGIA/IA). "
            "That is a study-process milestone, not a guarantee the plant will be built. "
            "Toggle to include projects still under study. ERCOT withholds some pre-FIS "
            "and not-yet-public small-generator requests from the public detail sheets."
            if not show_full_queue else
            "Showing every project on ERCOT's public Large Gen and Small Gen detail sheets. "
            "The GIS Summary tally can be higher because some requests are confidential "
            "until a Full Interconnection Study is requested or small-gen data is model-ready."
        )

        if len(df_view) == 0:
            st.warning("⚠️ **No projects match this view**")
            st.info("Toggle \"Show full public queue\" above to see all parsed projects.")
            return

        # Summary metrics — complete view, including any unmappable rows
        total_capacity = df_view['proposed_mw'].sum()
        total_projects = len(df_view)
        fuel_types = df_view['fuel'].nunique()
        
        cap_subtitle = (
            "Public detail sheets" if show_full_queue else "Signed IA (not construction)"
        )
        count_subtitle = (
            "Public Large+Small Gen sheets" if show_full_queue else "Signed interconnection agreement"
        )

        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-card-title">Total Planned Capacity</div>
                <div class="metric-card-value">{total_capacity:,.0f} MW</div>
                <div class="metric-card-subtitle">{cap_subtitle}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-card-title">Projects in Queue</div>
                <div class="metric-card-value">{total_projects:,}</div>
                <div class="metric-card-subtitle">{count_subtitle}</div>
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
    
        # Map section — mappable subset only
        st.subheader("Project Locations")
        if len(df_map) < len(df_view):
            st.caption(
                f"Map shows {len(df_map):,} of {len(df_view):,} projects in this view "
                f"({len(df_view) - len(df_map):,} lack usable Texas coordinates)."
            )

        deck = create_queue_map(df_map)
        if deck is None:
            st.warning("No mappable coordinates for this view. Tables below still use the full view totals.")
        else:
            st.pydeck_chart(deck, height=600, use_container_width=True)
            st.markdown(
            '<div style="text-align: center; padding: 12px 0; background-color: #f9fafb; '
            'border-top: 1px solid #e5e7eb; border-bottom: 1px solid #e5e7eb; margin: 16px 0;">'
            '<span style="margin-right: 24px; white-space: nowrap;">'
            '<span style="display: inline-block; width: 16px; height: 16px; '
            'background-color: rgb(200, 16, 46); border-radius: 50%; margin-right: 8px; '
            'vertical-align: middle; border: 1px solid rgba(0,0,0,0.15);"></span>'
            '<span style="font-size: 12px; color: #374151;"><b>Large Projects</b> (>70th percentile)</span>'
            '</span>'
            '<span style="margin-right: 24px; white-space: nowrap;">'
            '<span style="display: inline-block; width: 14px; height: 14px; '
            'background-color: rgb(160, 16, 46); border-radius: 50%; margin-right: 8px; '
            'vertical-align: middle; border: 1px solid rgba(0,0,0,0.15);"></span>'
            '<span style="font-size: 12px; color: #374151;"><b>Medium Projects</b> (40-70th percentile)</span>'
            '</span>'
            '<span style="white-space: nowrap;">'
            '<span style="display: inline-block; width: 12px; height: 12px; '
            'background-color: rgb(27, 54, 93); border-radius: 50%; margin-right: 8px; '
            'vertical-align: middle; border: 1px solid rgba(0,0,0,0.15);"></span>'
            '<span style="font-size: 12px; color: #374151;"><b>Small Projects</b> (<40th percentile)</span>'
            '</span>'
            '</div>',
            unsafe_allow_html=True
        )
        
        last_processed = get_last_updated(df_view)
        timestamp = get_file_modification_time("queue.parquet")
        view_label = (
            "full public Large+Small Gen detail sheets"
            if show_full_queue
            else "signed interconnection agreement (not a construction guarantee)"
        )
        st.info(
            f"**Showing: {view_label}.** "
            "Source: ERCOT GIS Report, republished monthly — not a real-time feed. "
            f"Last processed: {last_processed}."
        )

        st.markdown("---")

        # Data export
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("**Download Queue Data for Policy Analysis**")
        with col2:
            create_download_button(
                df=df_view,
                filename_prefix="interconnection_queue",
                label="Download Queue Data"
            )

        # Project breakdown by fuel type
        st.subheader("Queue Composition by Technology")

        fuel_summary = df_view.groupby('fuel').agg({
            'proposed_mw': 'sum',
            'project_name': 'count'
        }).round(0).sort_values('proposed_mw', ascending=False)

        fuel_summary.columns = ['Total Capacity (MW)', 'Number of Projects']
        fuel_summary['Avg Size (MW)'] = (fuel_summary['Total Capacity (MW)'] / fuel_summary['Number of Projects']).round(0)

        st.dataframe(fuel_summary, use_container_width=True)

        # Key insights
        st.subheader("Key Insights")

        dominant_fuel = fuel_summary.index[0]
        dominant_capacity = fuel_summary.iloc[0]['Total Capacity (MW)']
        dominant_pct = (dominant_capacity / total_capacity) * 100

        avg_project_size = df_view['proposed_mw'].mean()
        largest_project = df_view.loc[df_view['proposed_mw'].idxmax()]

        st.markdown(f"""
        - **Pipeline Scale**: {total_projects:,} projects representing {total_capacity:,.0f} MW of future capacity
        - **Dominant Technology**: {dominant_fuel} accounts for {dominant_pct:.1f}% of planned capacity
        - **Average Project Size**: {avg_project_size:.0f} MW per project
        - **Largest Project**: {largest_project['project_name']} ({largest_project['proposed_mw']:.0f} MW)
        - **Geographic Concentration**: Most projects located in West Texas (Panhandle wind corridor)
        - **Data Source**: ERCOT Generator Interconnection Status (GIS) Report
        """)

        # Technical notes
        with st.expander("Technical Notes"):
            st.markdown(f"""
            **Data Source:**
            - Source: ERCOT Generator Interconnection Status (GIS) Report
            - Update Frequency: Monthly (ERCOT republishes; this dashboard's ETL runs every 6 hours and picks up the newest available report)
            - Coverage: {view_label}
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
            - Project capacities range from {df_view['proposed_mw'].min():.0f} to {df_view['proposed_mw'].max():.0f} MW
            - {len(df_map)} of {len(df_view)} projects in this view are mapped (Texas coordinates)
            - Coordinates are county centroids with small jitter, not exact site locations — the source report gives county and substation name, not lat/lon
            """)

        # Render footer
        last_updated = get_last_updated(df_view)
        render_data_source_footer('queue', last_updated)

    except KeyError as e:
        st.error(f"❌ **Data Format Error**: Missing required column: {str(e)}")
        st.info("🔄 The data file may be corrupted. Try re-running the ETL script.")
        st.code("python etl/ercot_gis_queue_etl.py", language="bash")

    except pd.errors.ParserError:
        st.error(f"❌ **File Corrupted**: Unable to read queue data")
        st.info("🔄 The parquet file may be damaged. Re-run the ETL script.")
        st.code("python etl/ercot_gis_queue_etl.py", language="bash")

    except Exception as e:
        st.error(f"❌ **Unexpected error loading queue data**: {str(e)}")
        st.info("🔄 Try refreshing the page. If the issue persists, re-run the ETL script.")
        st.code("python etl/ercot_gis_queue_etl.py", language="bash")