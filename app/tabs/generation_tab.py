"""
Generation Map Tab

Displays Texas power generation facilities on an interactive map using real EIA data.
Shows plant locations, capacity, and fuel types from EIA Operating Generator Capacity API.

Data source: U.S. Energy Information Administration (EIA)
"""

import streamlit as st
import pandas as pd
import pydeck as pdk
from pathlib import Path

from utils.data_sources import render_data_source_footer
from utils.colors import get_fuel_color_rgba
from utils.loaders import get_last_updated


def load_generation_data() -> pd.DataFrame:
    """
    Load Texas power generation facilities data from parquet file.
    
    Returns:
        DataFrame with generation facility data
        
    Raises:
        FileNotFoundError if data file doesn't exist
    """
    data_path = Path(__file__).parent.parent.parent / "data" / "generation.parquet"
    
    if not data_path.exists():
        raise FileNotFoundError(f"Generation data not found at {data_path}")
    
    df = pd.read_parquet(data_path)
    return df


def calculate_generation_kpis(df: pd.DataFrame) -> dict:
    """
    Calculate key performance indicators for Texas generation.
    
    Args:
        df: Generation facilities DataFrame
        
    Returns:
        Dictionary with KPI values
    """
    total_plants = len(df)
    total_capacity = df['capacity_mw'].sum()
    
    # Fuel breakdown
    fuel_breakdown = df.groupby('fuel')['capacity_mw'].sum().sort_values(ascending=False)
    largest_fuel = fuel_breakdown.index[0]
    largest_fuel_pct = (fuel_breakdown.iloc[0] / total_capacity) * 100
    
    # Largest plant
    largest_plant = df.loc[df['capacity_mw'].idxmax()]
    
    return {
        'total_plants': total_plants,
        'total_capacity': total_capacity,
        'largest_fuel': largest_fuel,
        'largest_fuel_pct': largest_fuel_pct,
        'largest_plant_name': largest_plant['plant_name'],
        'largest_plant_capacity': largest_plant['capacity_mw'],
        'fuel_breakdown': fuel_breakdown
    }


def create_generation_map(df: pd.DataFrame) -> pdk.Deck:
    """
    Create pydeck map of Texas power generation facilities.
    
    Args:
        df: Generation facilities DataFrame
        
    Returns:
        Configured pydeck Deck
    """
    # Add colors based on fuel type
    df = df.copy()
    df['color'] = df['fuel'].apply(get_fuel_color_rgba)
    
    # Scale point size based on capacity (min 50, max 500 pixels)
    max_capacity = df['capacity_mw'].max()
    min_size, max_size = 50, 500
    df['size'] = df['capacity_mw'].apply(
        lambda x: min_size + (max_size - min_size) * (x / max_capacity)
    )
    
    # Create scatterplot layer
    layer = pdk.Layer(
        'ScatterplotLayer',
        df,
        get_position=['lon', 'lat'],
        get_color='color',
        get_radius='size',
        radius_scale=1,
        radius_min_pixels=8,
        radius_max_pixels=50,
        pickable=True,
        auto_highlight=True,
    )
    
    # Set view state centered on Texas
    view_state = pdk.ViewState(
        latitude=31.0,
        longitude=-99.0,
        zoom=5.8,
        pitch=0,
        bearing=0
    )
    
    # Create deck (tooltip will be handled by Streamlit pydeck)
    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_style='mapbox://styles/mapbox/light-v9',
    )
    
    return deck


def render():
    """Render the Generation Map tab."""
    st.header("⚡ Texas Power Generation Facilities")
    
    try:
        # Load generation data
        df = load_generation_data()
        
        # Calculate KPIs
        kpis = calculate_generation_kpis(df)
        
        # Data status indicator (using Streamlit info)
        st.success(f"✅ **Live Data**: EIA Power Plants Database - {kpis['total_plants']} facilities from EIA Operating Generator Capacity API")
        
        # Display KPIs
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total Plants",
                f"{kpis['total_plants']:,}",
                help="Number of power generation facilities in Texas"
            )
        
        with col2:
            st.metric(
                "Total Capacity", 
                f"{kpis['total_capacity']:,.0f} MW",
                help="Combined nameplate capacity of all Texas generators"
            )
        
        with col3:
            st.metric(
                "Dominant Fuel",
                kpis['largest_fuel'],
                f"{kpis['largest_fuel_pct']:.1f}% of capacity",
                help="Primary fuel type by total installed capacity"
            )
        
        with col4:
            st.metric(
                "Largest Plant",
                kpis['largest_plant_name'][:20] + ("..." if len(kpis['largest_plant_name']) > 20 else ""),
                f"{kpis['largest_plant_capacity']:,.0f} MW",
                help="Highest capacity power generation facility"
            )
        
        # Interactive map
        st.subheader("🗺️ Interactive Facility Map")
        
        deck = create_generation_map(df)
        st.pydeck_chart(deck, use_container_width=True)
        
        # Legend
        st.markdown("""
        **Map Legend:**
        - 🔵 **Point Size**: Proportional to plant capacity (MW)  
        - 🎨 **Colors**: Fuel type (hover for details)
        - 📍 **Click**: View facility details
        """)
        
        # Fuel breakdown chart
        st.subheader("📊 Generation Mix by Fuel Type")
        
        fuel_df = pd.DataFrame({
            'Fuel Type': kpis['fuel_breakdown'].index,
            'Capacity (MW)': kpis['fuel_breakdown'].values,
            'Percentage': (kpis['fuel_breakdown'].values / kpis['total_capacity'] * 100).round(1)
        })
        
        # Create columns for the chart and table
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.bar_chart(
                fuel_df.set_index('Fuel Type')['Capacity (MW)'],
                use_container_width=True
            )
        
        with col2:
            st.dataframe(
                fuel_df,
                use_container_width=True,
                hide_index=True
            )
        
        # Summary insights
        st.subheader("🔍 Key Insights")
        
        total_renewable = kpis['fuel_breakdown'].get('SOLAR', 0) + kpis['fuel_breakdown'].get('WIND', 0)
        renewable_pct = (total_renewable / kpis['total_capacity']) * 100
        
        st.markdown(f"""
        - **Grid Scale**: Texas operates {kpis['total_plants']:,} power plants with {kpis['total_capacity']:,.0f} MW total capacity
        - **Fuel Diversity**: {len(kpis['fuel_breakdown'])} different fuel types provide generation
        - **Renewable Energy**: Solar and wind account for {renewable_pct:.1f}% of installed capacity
        - **Geographic Distribution**: Plants spread across all regions of Texas for grid reliability
        - **Data Currency**: Live EIA data updated from official government sources
        """)
        
        # Technical notes
        with st.expander("📋 Technical Notes"):
            st.markdown(f"""
            **Data Processing:**
            - Source: EIA Operating Generator Capacity API (electricity/operating-generator-capacity)
            - Coverage: All registered generators ≥1 MW in Texas (State ID: TX)
            - Aggregation: Individual generators grouped by plant facility
            - Geocoding: Plant locations approximated using regional mapping
            - Last Updated: {df['last_updated'].iloc[0][:19]}Z
            
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
        last_updated = get_last_updated(df)
        render_data_source_footer('generation', last_updated)
        
    except FileNotFoundError as e:
        st.error(f"""
        **Generation data not available**: {e}
        
        To generate the data, run:
        ```bash
        python etl/eia_plants_etl.py
        ```
        """)
        
    except Exception as e:
        st.error(f"Error loading generation data: {e}")
        st.info("Please ensure the ETL script has been run to generate the data file.")

import streamlit as st
import pandas as pd
import pydeck as pdk

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

# End of file - old stub content removed
