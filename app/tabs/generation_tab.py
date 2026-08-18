import streamlit as st
import pandas as pd
import pydeck as pdk
import math
import os
from datetime import datetime
from pathlib import Path

from utils.data_sources import render_data_source_footer
from utils.colors import FUEL_COLORS_HEX
from utils.loaders import get_last_updated, load_parquet
from utils.export import create_download_button
from utils.advocacy import render_advocacy_message


def generation_period_subtitle(df: pd.DataFrame) -> str:
    """Subtitle for reported generation metric from ETL period columns."""
    if 'generation_period_start' in df.columns and 'generation_period_end' in df.columns:
        start = df['generation_period_start'].iloc[0]
        end = df['generation_period_end'].iloc[0]
        return f"EIA-923 Facility-Fuel ({start} to {end})"
    return "EIA-923 Facility-Fuel (3-mo avg)"


def clean_and_aggregate_facilities(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and aggregate generation facilities data.
    Groups by facility and sums both capacity and actual generation while handling missing coordinates.
    """
    # Remove rows with missing essential data
    df_clean = df.dropna(subset=['plant_name', 'capacity_mw', 'fuel'])
    
    # Drop rows without real coordinates — do not substitute defaults
    df_clean = df_clean.dropna(subset=['lat', 'lon'])
    
    # Prepare aggregation dict - always include capacity
    agg_dict = {
        'capacity_mw': 'sum',
        'last_updated': 'first'
    }
    
    # Add actual_generation_mw if it exists in the data
    if 'actual_generation_mw' in df_clean.columns:
        agg_dict['actual_generation_mw'] = 'sum'
    if 'generation_is_estimated' in df_clean.columns:
        agg_dict['generation_is_estimated'] = 'max'
    if 'generation_period_start' in df_clean.columns:
        agg_dict['generation_period_start'] = 'first'
    if 'generation_period_end' in df_clean.columns:
        agg_dict['generation_period_end'] = 'first'

    # Group by plant and aggregate
    aggregated = df_clean.groupby(['plant_name', 'fuel', 'lat', 'lon']).agg(agg_dict).reset_index()
    
    return aggregated


def create_fixed_texas_map(df: pd.DataFrame) -> pdk.Deck:
    """
    Create a Texas-focused map similar to ERCOT price maps with realistic facility distribution.
    """
    df = df.copy()
    
    # Add colors based on fuel type (similar to ERCOT color coding)
    def get_color(fuel):
        color_hex = FUEL_COLORS_HEX.get(str(fuel), '#a0a0a0')
        # Convert hex to RGB with good opacity
        color_hex = color_hex.lstrip('#')
        return [int(color_hex[0:2], 16), int(color_hex[2:4], 16), int(color_hex[4:6], 16), 180]
    
    df['color'] = df['fuel'].apply(get_color)
    
    # Use actual generation for radius scaling (not nameplate capacity)
    # This shows real output, not theoretical maximum
    generation_col = 'actual_generation_mw'
    if generation_col not in df.columns or df[generation_col].isna().all():
        generation_col = 'capacity_mw'
    max_generation = df[generation_col].max()
    min_generation = df[generation_col].min()
    
    def ercot_style_radius(generation):
        """Scale radius based on actual generation - clearer size differences."""
        if max_generation == min_generation:
            return 12
        
        # Use square root scaling for better visual distinction
        normalized = (generation - min_generation) / (max_generation - min_generation)
        
        # ERCOT-style scaling: small plants visible, large plants prominent
        sqrt_scaled = math.sqrt(normalized)
        return 6 + (sqrt_scaled * 25)  # Range: 6-31 pixels
    
    df['radius'] = df[generation_col].apply(ercot_style_radius)
    
    # Pre-format numeric values for the tooltip. pydeck's tooltip templating
    # only supports plain {field_name} substitution — it does NOT support
    # Python format specifiers like {field:.0f}, which previously rendered
    # literally as the string "{actual_generation_mw:.0f}" in the UI instead
    # of a formatted number. Rounding here and referencing the new columns
    # in the html template is the correct fix.
    df['actual_generation_mw_display'] = df.get(
        'actual_generation_mw', df['capacity_mw']
    ).round(0).astype(int)
    df['capacity_mw_display'] = df['capacity_mw'].round(0).astype(int)
    
    # Tooltip configuration - show both actual generation and capacity
    if 'actual_generation_mw' in df.columns:
        tooltip = {
            "html": "<b>{plant_name}</b><br/>Fuel: {fuel}<br/>Actual: {actual_generation_mw_display} MW<br/>Capacity: {capacity_mw_display} MW",
            "style": {
                "backgroundColor": "white",
                "color": "black",
                "fontSize": "14px",
                "borderRadius": "6px",
                "padding": "8px 12px",
                "boxShadow": "0 2px 8px rgba(0,0,0,0.15)"
            }
        }
    else:
        tooltip = {
            "html": "<b>{plant_name}</b><br/>Fuel: {fuel}<br/>Capacity: {capacity_mw} MW",
            "style": {
                "backgroundColor": "white",
                "color": "black",
                "fontSize": "14px",
                "borderRadius": "6px",
                "padding": "8px 12px",
                "boxShadow": "0 2px 8px rgba(0,0,0,0.15)"
            }
        }
    
    # Create scatterplot layer with ERCOT-style appearance
    layer = pdk.Layer(
        'ScatterplotLayer',
        df,
        get_position=['lon', 'lat'],
        get_color='color',
        get_radius='radius',
        radius_scale=1,
        radius_min_pixels=4,     # Smaller minimum for better precision
        radius_max_pixels=50,    # Reasonable maximum
        pickable=True,
        auto_highlight=True,
        get_line_color=[255, 255, 255, 150],  # White outline like ERCOT
        stroked=True,
        filled=True,
        line_width_min_pixels=1,
        line_width_max_pixels=2,
        opacity=0.8
    )
    
    # Texas-focused locked viewport - MAXIMUM ZOOM OUT (4.7 - NEW VALUE!)
    view_state = pdk.ViewState(
        latitude=31.0,
        longitude=-99.5,
        zoom=4.7,
        pitch=0,
        min_zoom=4.7,
        max_zoom=4.7,
    )
    
    return pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_style='mapbox://styles/mapbox/light-v10',
        tooltip=tooltip,  # type: ignore
        views=[pdk.View(type='MapView', controller=False)]
    )


def render_legend_and_counts(df: pd.DataFrame):
    """Horizontal legend matching Fuel Mix tab format - under map"""
    
    # Get fuel type data
    fuel_stats = df.groupby('fuel').agg({
        'plant_name': 'count',
        'capacity_mw': 'sum'
    }).reset_index()
    
    fuel_stats.columns = ['Fuel Type', 'Plants', 'Capacity (MW)']
    fuel_stats = fuel_stats.sort_values('Capacity (MW)', ascending=False)
    
    # Build horizontal legend HTML matching Fuel Mix style
    legend_items = []
    for _, row in fuel_stats.iterrows():
        fuel = row['Fuel Type']
        plants = int(row['Plants'])
        capacity = row['Capacity (MW)']
        
        # Get color
        color = FUEL_COLORS_HEX.get(fuel.upper(), '#CCCCCC')
        
        legend_items.append(
            f'<span style="margin-right: 20px; white-space: nowrap;">'
            f'<span style="display: inline-block; width: 12px; height: 12px; '
            f'background-color: {color}; margin-right: 6px; vertical-align: middle; '
            f'border: 1px solid rgba(0,0,0,0.15);"></span>'
            f'<span style="font-size: 12px; color: #374151;">{fuel.title()}</span>'
            f'</span>'
        )
    
    # Render horizontal legend
    st.markdown(
        f'<div style="text-align: center; padding: 12px 0; background-color: #f9fafb; '
        f'border-top: 1px solid #e5e7eb; border-bottom: 1px solid #e5e7eb; margin: 16px 0;">'
        f'{"".join(legend_items)}'
        f'</div>',
        unsafe_allow_html=True
    )


def render():
    """Render the Generation Map tab with comprehensive error handling."""
    # Minimal header - ultra compact
    st.markdown("### Texas Power Generation Facilities")
    
    # Compact advocacy message - single line, non-intrusive
    st.markdown("""
    <div style="padding: 8px 12px; background-color: #f8f9fa; border-left: 3px solid #1f4788; 
                margin: 12px 0 20px 0; font-size: 14px; color: #4b5563; line-height: 1.5;">
        <strong>TAB Policy:</strong> Texas Association of Business advocates for streamlined permitting 
        and market-driven investment to meet Texas' growing energy demand. 
        <a href="https://www.txbiz.org/policy-priorities/energy/" target="_blank" 
           style="color: #1f4788; text-decoration: none; font-weight: 500;">Learn more →</a>
    </div>
    """, unsafe_allow_html=True)
    
    try:
        # Load generation data via the canonical loader — this provides
        # schema normalization, type coercion, validation, and graceful
        # degradation consistent with every other tab (previously this
        # tab bypassed load_parquet() with a raw pd.read_parquet() call,
        # skipping all of the above).
        df = load_parquet("generation.parquet", "generation", allow_empty=True)
        
        # Check if data is empty
        if len(df) == 0:
            st.warning("⚠️ **No generation facilities found**")
            st.info("🔄 The data file is empty. Re-run the ETL script.")
            st.code("python etl/eia_plants_etl.py", language="bash")
            return
        
        # Clean and aggregate data
        clean_df = clean_and_aggregate_facilities(df)
        gen_subtitle = generation_period_subtitle(clean_df)

        if 'actual_generation_mw' not in clean_df.columns or clean_df['actual_generation_mw'].isna().all():
            st.warning("⚠️ **No measured generation data in this file**")
            st.info("Re-run the ETL to refresh from EIA facility-fuel (Form EIA-923).")
            st.code("python etl/eia_plants_etl.py", language="bash")
            return
        
        total_plants = len(clean_df)
        total_capacity = clean_df['capacity_mw'].sum()
        total_actual_gen = clean_df['actual_generation_mw'].sum()
        capacity_factor = (total_actual_gen / total_capacity * 100) if total_capacity > 0 else 0
        
        fuel_breakdown_actual = clean_df.groupby('fuel')['actual_generation_mw'].sum().sort_values(ascending=False)
        largest_plant = clean_df.loc[clean_df['actual_generation_mw'].idxmax()]
        
        # Display KPIs - Unified metric card style matching Fuel Mix tab
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-card-title">Total Plants</div>
                <div class="metric-card-value">{total_plants:,}</div>
                <div class="metric-card-subtitle">With Measured EIA-923 Data</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-card-title">Reported Generation ⓘ</div>
                <div class="metric-card-value">{total_actual_gen:,.0f} MW</div>
                <div class="metric-card-subtitle">{gen_subtitle}</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-card-title">Capacity Factor</div>
                <div class="metric-card-value">{capacity_factor:.1f}%</div>
                <div class="metric-card-subtitle">Reported vs Nameplate</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            plant_name = largest_plant['plant_name']
            display_name = plant_name[:15] + "..." if len(plant_name) > 15 else plant_name
            largest_gen = largest_plant['actual_generation_mw']
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-card-title">Top Producer</div>
                <div class="metric-card-value" style="font-size: 1.5rem;">{display_name}</div>
                <div class="metric-card-subtitle">{largest_gen:,.0f} MW Output</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Interactive map - full width, shorter height
        st.subheader("Interactive Facility Map")
        
        deck = create_fixed_texas_map(clean_df)
        st.pydeck_chart(deck, height=500, use_container_width=True)
        
        # Horizontal legend right under map - matching Fuel Mix style
        render_legend_and_counts(clean_df)
        
        # Data status indicator with timestamp - MOVED BELOW MAP for better UX
        file_path = Path(__file__).parent.parent.parent / "data" / "generation.parquet"
        timestamp_str = "Unknown"
        if file_path.exists():
            mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            timestamp_str = mod_time.strftime('%Y-%m-%d %H:%M:%S')
        
        st.success(f"**Live Data**: EIA Power Plants Database - {len(clean_df)} facilities from EIA Operating Generator Capacity API - Last Updated: {timestamp_str}")
        
        # Data Export Section
        st.markdown("---")
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("**Download Generation Facilities Data**")
        with col2:
            create_download_button(
                df=clean_df,
                filename_prefix="generation_facilities",
                label="Download Facilities Data"
            )
        
        # Fuel breakdown chart - using actual generation
        st.subheader("Generation Mix by Fuel Type")
        
        fuel_chart_df = pd.DataFrame({
            'Fuel Type': fuel_breakdown_actual.index,
            'Actual Generation (MW)': fuel_breakdown_actual.values,
            'Percentage': (fuel_breakdown_actual.values / fuel_breakdown_actual.sum() * 100).round(1)
        })
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.bar_chart(fuel_chart_df.set_index('Fuel Type')['Actual Generation (MW)'])
        
        with col2:
            st.dataframe(fuel_chart_df, hide_index=True)
        
        # Summary insights
        st.subheader("🔍 Key Insights")
        
        renewable_actual = fuel_breakdown_actual.get('SOLAR', 0) + fuel_breakdown_actual.get('WIND', 0)
        renewable_pct = (renewable_actual / fuel_breakdown_actual.sum()) * 100
        storage_actual = fuel_breakdown_actual.get('STORAGE', 0)
        storage_pct = (storage_actual / fuel_breakdown_actual.sum()) * 100
        
        st.markdown(f"""
        - **Grid Scale**: {total_plants:,} facilities with measured EIA-923 output and {total_capacity:,.0f} MW nameplate capacity
        - **Generation Data**: {total_actual_gen:,.0f} MW average output from EIA facility-fuel (Jul–Sep 2024)
        - **Nameplate vs. Output**: Reported output is {capacity_factor:.1f}% of nameplate capacity
        - **Fuel Diversity**: {len(fuel_breakdown_actual)} fuel types in the measured dataset
        - **Renewable Energy**: Solar and wind account for {renewable_pct:.1f}% of reported generation
        - **Battery Storage**: {int(storage_actual):,} MW ({storage_pct:.1f}% of reported generation)
        - **Geographic Distribution**: EIA Form 860 Schedule 2 plant coordinates
        - **Data Currency**: EIA operating capacity + facility-fuel; not real-time
        """)
        
        # Technical notes
        with st.expander("Technical Notes"):
            st.markdown(f"""
            **Data Processing:**
            - Source: EIA Operating Generator Capacity API (electricity/operating-generator-capacity)
            - Coverage: All registered generators ≥1 MW in Texas (State ID: TX)
            - Aggregation: Individual generators grouped by plant facility
            - Geocoding: EIA Form 860 Schedule 2 plant latitude/longitude (Plant Code join)
            - Generation source: EIA facility-fuel (Form EIA-923), Jul–Sep 2024 average where available
            - Last Updated: {get_last_updated(df)[:19]}Z
            
            **Capacity Notes:**
            - **Nameplate Capacity**: Theoretical maximum output under ideal conditions ({total_capacity:,.0f} MW total)
            - **Reported Generation**: Measured from EIA-923 facility-fuel only (plants without data excluded)
            - **Capacity Factor**: Varies by fuel type - gas ~50-60%, wind ~35%, solar ~25%, nuclear ~90%
            - **Battery Storage**: Included as generation source - provides grid flexibility and demand response
            - **Not Real-Time**: These are 3-month averages, not current generation levels
            
            **Fuel Type Mapping:**
            - Gas: All natural gas technologies (combined cycle, combustion turbine, steam)
            - Solar: Solar photovoltaic installations
            - Wind: Onshore wind turbines
            - Storage: Battery energy storage systems ({len(clean_df[clean_df['fuel'] == 'STORAGE'])} facilities, {int(storage_actual):,} MW)
            - Other: Coal, nuclear, hydroelectric, and miscellaneous sources
            
            **Map Visualization:**
            - Point size scaled by actual generation (not nameplate capacity)
            - Colors indicate primary fuel type
            - Interactive tooltips show plant details
            - Geographic coordinates from EIA Form 860 (not approximated)
            """)
        
        # Render footer
        render_data_source_footer('generation', get_last_updated(df))
        
    except KeyError as e:
        st.error(f"❌ **Data Format Error**: Missing required column: {str(e)}")
        st.info("🔄 The data file may be corrupted. Try re-running the ETL script.")
        st.code("python etl/eia_plants_etl.py", language="bash")
        
    except pd.errors.ParserError as e:
        st.error(f"❌ **File Corrupted**: Unable to read generation data")
        st.info("🔄 The parquet file may be damaged. Re-run the ETL script to regenerate.")
        st.code("python etl/eia_plants_etl.py", language="bash")
        
    except Exception as e:
        st.error(f"❌ **Unexpected error loading generation data**: {str(e)}")
        st.info("🔄 Try refreshing the page. If the issue persists, re-run the ETL script.")
        st.code("python etl/eia_plants_etl.py", language="bash")
