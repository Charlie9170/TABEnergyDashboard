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
    # Add colors based on fuel type (convert to RGBA format for pydeck)
    df = df.copy()
    df['color'] = df['fuel'].apply(lambda x: get_fuel_color_rgba(x, alpha=180))
    
    # Scale point size based on capacity with better visual scaling
    max_capacity = df['capacity_mw'].max()
    min_capacity = df['capacity_mw'].min()
    
    def scale_radius(capacity):
        """Scale plant capacity to appropriate visual radius (10-200 pixels)."""
        if max_capacity == min_capacity:
            return 50
        normalized = (capacity - min_capacity) / (max_capacity - min_capacity)
        return 15 + (normalized * 185)  # Range from 15 to 200 pixels
    
    df['radius'] = df['capacity_mw'].apply(scale_radius)
    
    # Create scatterplot layer with enhanced styling
    layer = pdk.Layer(
        'ScatterplotLayer',
        df,
        get_position=['lon', 'lat'],
        get_color='color',
        get_radius='radius',
        radius_scale=1,
        radius_min_pixels=8,
        radius_max_pixels=50,
        pickable=True,
        auto_highlight=True,
        stroked=True,
        filled=True,
        get_line_color=[255, 255, 255, 100],  # White outline
        line_width_min_pixels=1,
        opacity=0.8,
    )
    
    # Set view state centered on Texas with better zoom
    view_state = pdk.ViewState(
        latitude=31.0,
        longitude=-99.0,
        zoom=6.2,
        pitch=0,
        bearing=0,
        height=600
    )
    
    # Create deck with better map style (tooltips handled by Streamlit)
    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_style='mapbox://styles/mapbox/light-v10',
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
            # Find the dominant fuel (excluding OTHER if possible)
            fuel_by_capacity = kpis['fuel_breakdown']
            if len(fuel_by_capacity) > 1 and fuel_by_capacity.index[0] == 'OTHER':
                dominant_fuel = fuel_by_capacity.index[1]  # Use second largest if OTHER is first
                dominant_pct = (fuel_by_capacity.iloc[1] / kpis['total_capacity']) * 100
            else:
                dominant_fuel = fuel_by_capacity.index[0]
                dominant_pct = (fuel_by_capacity.iloc[0] / kpis['total_capacity']) * 100
                
            st.metric(
                "Dominant Fuel",
                dominant_fuel,
                f"{dominant_pct:.1f}% of capacity",
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
        
        # Enhanced legend with fuel colors
        st.markdown("**Map Legend:**")
        
        # Create color legend in columns
        fuel_counts = df['fuel'].value_counts()
        cols = st.columns(min(5, len(fuel_counts)))  # Max 5 columns
        
        from utils.colors import FUEL_COLORS_HEX
        
        for i, (fuel, count) in enumerate(fuel_counts.items()):
            col_idx = i % len(cols)
            color = FUEL_COLORS_HEX.get(str(fuel).upper(), '#64748b')
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
