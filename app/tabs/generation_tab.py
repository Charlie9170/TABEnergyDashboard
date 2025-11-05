import streamlit as st
import pandas as pd
import pydeck as pdk
import math
from pathlib import Path

from utils.data_sources import render_data_source_footer
from utils.colors import FUEL_COLORS_HEX
from utils.loaders import get_last_updated
from utils.export import create_download_button


def clean_and_aggregate_facilities(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and aggregate generation facilities data.
    Groups by facility and sums capacity while handling missing coordinates.
    """
    # Remove rows with missing essential data
    df_clean = df.dropna(subset=['plant_name', 'capacity_mw', 'fuel'])
    
    # Handle missing coordinates by using regional approximations
    df_clean = df_clean.copy()
    df_clean['lat'] = df_clean['lat'].fillna(31.0)
    df_clean['lon'] = df_clean['lon'].fillna(-99.0)
    
    # Group by plant and aggregate
    aggregated = df_clean.groupby(['plant_name', 'fuel', 'lat', 'lon']).agg({
        'capacity_mw': 'sum',
        'last_updated': 'first'
    }).reset_index()
    
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
    
    # ERCOT-style radius scaling based on capacity
    max_capacity = df['capacity_mw'].max()
    min_capacity = df['capacity_mw'].min()
    
    def ercot_style_radius(capacity):
        """Scale radius similar to ERCOT maps - clearer size differences."""
        if max_capacity == min_capacity:
            return 12
        
        # Use square root scaling for better visual distinction
        normalized = (capacity - min_capacity) / (max_capacity - min_capacity)
        
        # ERCOT-style scaling: small plants visible, large plants prominent
        sqrt_scaled = math.sqrt(normalized)
        return 6 + (sqrt_scaled * 25)  # Range: 6-31 pixels
    
    df['radius'] = df['capacity_mw'].apply(ercot_style_radius)
    
    # Tooltip configuration
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
    """Render fuel type legend with colors and counts."""
    st.markdown("**Map Legend:**")
    
    # Create color legend in columns
    fuel_counts = df['fuel'].value_counts()
    cols = st.columns(min(5, len(fuel_counts)))
    
    for i, (fuel, count) in enumerate(fuel_counts.items()):
        col_idx = i % len(cols)
        color = FUEL_COLORS_HEX.get(str(fuel), '#a0a0a0')
        capacity = df[df['fuel'] == fuel]['capacity_mw'].sum()
        
        with cols[col_idx]:
            st.markdown(
                f'''
                <div style="display: flex; align-items: center; margin-bottom: 4px;">
                    <div style="width: 12px; height: 12px; background-color: {color}; 
                                border-radius: 50%; margin-right: 8px; border: 1px solid #ddd;"></div>
                    <span style="font-size: 13px;"><b>{fuel}</b>: {count} plants ({capacity:,.0f} MW)</span>
                </div>
                ''', 
                unsafe_allow_html=True
            )
    
    st.markdown("""
    - 📏 **Point Size**: Proportional to plant capacity (MW)  
    - 📍 **Hover**: View detailed facility information
    """)


def render():
    """Render the Generation Map tab with comprehensive error handling."""
    # Minimal header - ultra compact
    st.markdown("### Texas Power Generation Facilities")
    
    try:
        # Load generation data
        data_path = Path(__file__).parent.parent.parent / "data" / "generation.parquet"
        
        # Check if file exists
        if not data_path.exists():
            st.warning("⚠️ **Generation data not available**")
            st.info("Run the ETL script to fetch power plant data from EIA.")
            st.code("python etl/eia_plants_etl.py", language="bash")
            return
            
        df = pd.read_parquet(data_path)
        
        # Check if data is empty
        if len(df) == 0:
            st.warning("⚠️ **No generation facilities found**")
            st.info("🔄 The data file is empty. Re-run the ETL script.")
            st.code("python etl/eia_plants_etl.py", language="bash")
            return
        
        # Clean and aggregate data
        clean_df = clean_and_aggregate_facilities(df)
        
        # Calculate KPIs
        total_plants = len(clean_df)
        total_capacity = clean_df['capacity_mw'].sum()
        fuel_breakdown = clean_df.groupby('fuel')['capacity_mw'].sum().sort_values(ascending=False)
        largest_plant = clean_df.loc[clean_df['capacity_mw'].idxmax()]
        
        # Display KPIs - Unified metric card style matching Fuel Mix tab
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-card-title">Total Plants</div>
                <div class="metric-card-value">{total_plants:,}</div>
                <div class="metric-card-subtitle">Texas Generation Facilities</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-card-title">Total Capacity</div>
                <div class="metric-card-value">{total_capacity:,.0f} MW</div>
                <div class="metric-card-subtitle">Combined Nameplate Capacity</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            # Find the dominant fuel
            if len(fuel_breakdown) > 1 and fuel_breakdown.index[0] == 'OTHER':
                dominant_fuel = fuel_breakdown.index[1]
                dominant_pct = (fuel_breakdown.iloc[1] / total_capacity) * 100
            else:
                dominant_fuel = fuel_breakdown.index[0]
                dominant_pct = (fuel_breakdown.iloc[0] / total_capacity) * 100
                
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-card-title">Dominant Fuel</div>
                <div class="metric-card-value">{dominant_fuel}</div>
                <div class="metric-card-subtitle">{dominant_pct:.1f}% of Capacity</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            plant_name = largest_plant['plant_name']
            display_name = plant_name[:15] + "..." if len(plant_name) > 15 else plant_name
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-card-title">Largest Plant</div>
                <div class="metric-card-value" style="font-size: 1.5rem;">{display_name}</div>
                <div class="metric-card-subtitle">{largest_plant['capacity_mw']:,.0f} MW</div>
            </div>
            """, unsafe_allow_html=True)
        
        # Interactive map - full width, shorter height
        st.subheader("Interactive Facility Map")
        
        deck = create_fixed_texas_map(clean_df)
        st.pydeck_chart(deck, height=500, use_container_width=True)
        
        # Data status indicator - MOVED BELOW MAP for better UX
        st.success(f"**Live Data**: EIA Power Plants Database - {len(clean_df)} facilities from EIA Operating Generator Capacity API")
        
        # Enhanced legend with fuel colors
        render_legend_and_counts(clean_df)
        
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
        
        # Fuel breakdown chart
        st.subheader("Generation Mix by Fuel Type")
        
        fuel_chart_df = pd.DataFrame({
            'Fuel Type': fuel_breakdown.index,
            'Capacity (MW)': fuel_breakdown.values,
            'Percentage': (fuel_breakdown.values / fuel_breakdown.sum() * 100).round(1)
        })
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.bar_chart(fuel_chart_df.set_index('Fuel Type')['Capacity (MW)'])
        
        with col2:
            st.dataframe(fuel_chart_df, hide_index=True)
        
        # Summary insights
        st.subheader("🔍 Key Insights")
        
        renewable_capacity = fuel_breakdown.get('SOLAR', 0) + fuel_breakdown.get('WIND', 0)
        renewable_pct = (renewable_capacity / fuel_breakdown.sum()) * 100
        
        st.markdown(f"""
        - **Grid Scale**: Texas operates {total_plants:,} power plants with {total_capacity:,.0f} MW total capacity
        - **Fuel Diversity**: {len(fuel_breakdown)} different fuel types provide generation
        - **Renewable Energy**: Solar and wind account for {renewable_pct:.1f}% of installed capacity
        - **Geographic Distribution**: Plants spread across all regions of Texas for grid reliability
        - **Data Currency**: Live EIA data updated from official government sources
        """)
        
        # Technical notes
        with st.expander("Technical Notes"):
            st.markdown(f"""
            **Data Processing:**
            - Source: EIA Operating Generator Capacity API (electricity/operating-generator-capacity)
            - Coverage: All registered generators ≥1 MW in Texas (State ID: TX)
            - Aggregation: Individual generators grouped by plant facility
            - Geocoding: Plant locations approximated using regional mapping
            - Last Updated: {get_last_updated(df)[:19]}Z
            
            **Fuel Type Mapping:**
            - Gas: All natural gas technologies (combined cycle, combustion turbine, steam)
            - Solar: Solar photovoltaic installations
            - Wind: Onshore wind turbines
            - Storage: Battery energy storage systems
            - Other: Coal, nuclear, hydroelectric, and miscellaneous sources
            
            **Map Visualization:**
            - Point size scaled by nameplate capacity
            - Colors indicate primary fuel type
            - Interactive tooltips show plant details
            - Geographic coordinates estimated for visualization purposes
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
