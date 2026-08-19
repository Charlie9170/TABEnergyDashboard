import logging
import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.graph_objects as go
import math

from utils.data_sources import render_data_source_footer, render_freshness_banner
from utils.colors import FUEL_COLORS_HEX, get_fuel_color_hex
from utils.loaders import get_last_updated, load_parquet
from utils.export import create_download_button

logger = logging.getLogger(__name__)


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
    st.subheader(
        "Texas Power Generation Facilities",
        help="Texas plants with measured EIA-923 generation.",
    )
    
    # Compact advocacy message - single line, non-intrusive
    st.markdown("""
    <div style="padding: 8px 12px; background-color: #f8f9fa; border-left: 3px solid #1f4788; 
                margin: 12px 0 8px 0; font-size: 14px; color: #4b5563; line-height: 1.5;">
        <strong>TAB Policy:</strong> Texas Association of Business advocates for streamlined permitting 
        and market-driven investment to meet Texas' growing energy demand.
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
            logger.warning("Generation data unavailable: generation.parquet is empty")
            st.warning("Generation data temporarily unavailable.")
            return
        
        # Clean and aggregate data
        clean_df = clean_and_aggregate_facilities(df)
        gen_subtitle = generation_period_subtitle(clean_df)

        if 'actual_generation_mw' not in clean_df.columns or clean_df['actual_generation_mw'].isna().all():
            logger.warning(
                "Generation data has no measured actual_generation_mw values "
                "(column present=%s)", 'actual_generation_mw' in clean_df.columns
            )
            st.warning("Generation data temporarily unavailable.")
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
                <div class="metric-card-title">Reported Generation</div>
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
        st.subheader("Facility Map")
        
        deck = create_fixed_texas_map(clean_df)
        st.pydeck_chart(deck, height=500, use_container_width=True)
        
        # Horizontal legend right under map - matching Fuel Mix style
        render_legend_and_counts(clean_df)
        render_freshness_banner("EIA Generation Facilities", get_last_updated(df))
        
        # Fuel breakdown chart - using actual generation
        st.subheader("Generation Mix by Fuel Type")
        
        fuel_chart_df = pd.DataFrame({
            'Fuel Type': fuel_breakdown_actual.index,
            'Actual Generation (MW)': fuel_breakdown_actual.values,
            'Percentage': (fuel_breakdown_actual.values / fuel_breakdown_actual.sum() * 100).round(1)
        })
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Plotly instead of st.bar_chart: Streamlit 1.45.1 pins altair<6,
            # which raises TypedDict `closed=` on Streamlit Cloud Python 3.14.
            mix_series = fuel_chart_df.set_index('Fuel Type')['Actual Generation (MW)']
            fig = go.Figure(
                data=[
                    go.Bar(
                        x=mix_series.index.astype(str),
                        y=mix_series.values,
                        marker_color=[get_fuel_color_hex(str(fuel)) for fuel in mix_series.index],
                        hovertemplate='%{x}: %{y:,.0f} MW<extra></extra>',
                    )
                ]
            )
            fig.update_layout(
                xaxis_title="Fuel Type",
                yaxis_title="Actual Generation (MW)",
                height=350,
                margin=dict(t=20, r=20, b=40, l=60),
                showlegend=False,
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.dataframe(fuel_chart_df, hide_index=True)
        
        # Summary insights
        st.subheader("Key Insights")
        
        renewable_actual = fuel_breakdown_actual.get('SOLAR', 0) + fuel_breakdown_actual.get('WIND', 0)
        renewable_pct = (renewable_actual / fuel_breakdown_actual.sum()) * 100
        storage_actual = fuel_breakdown_actual.get('STORAGE', 0)
        storage_pct = (storage_actual / fuel_breakdown_actual.sum()) * 100
        
        st.markdown(f"""
        - **Renewable share**: Solar and wind account for {renewable_pct:.1f}% of reported generation
        - **Battery storage**: {int(storage_actual):,} MW ({storage_pct:.1f}% of reported generation)
        - **Nameplate capacity**: {total_capacity:,.0f} MW across these plants — reported output is a three-month average, not current real-time generation
        """)
        
        with st.expander("Technical Notes"):
            st.markdown(f"""
            - Reported generation is measured EIA-923 facility-fuel for **{gen_subtitle}**. Plants without measured data are excluded.
            - Nameplate capacity is theoretical maximum output; it is not the same as reported generation.
            - Map point size is scaled by reported generation, not nameplate capacity.
            - Coordinates come from EIA Form 860 Schedule 2 (plant latitude/longitude), not approximated locations.
            """)
        
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

        period_label = None
        if 'generation_period_start' in clean_df.columns and 'generation_period_end' in clean_df.columns:
            period_label = (
                f"{clean_df['generation_period_start'].iloc[0]} to "
                f"{clean_df['generation_period_end'].iloc[0]}"
            )
        render_data_source_footer(
            'generation',
            get_last_updated(df),
            data_through=period_label,
        )
        
    except KeyError:
        logger.exception("Generation tab: missing required column")
        st.warning("Generation data temporarily unavailable.")

    except pd.errors.ParserError:
        logger.exception("Generation tab: unable to read generation data")
        st.warning("Generation data temporarily unavailable.")

    except Exception:
        logger.exception("Generation tab: unexpected error")
        st.warning("Generation data temporarily unavailable.")
