import streamlit as st
import pandas as pd
import pydeck as pdk
import math
from pathlib import Path

from utils.data_sources import render_data_source_footer
from utils.colors import FUEL_COLORS_HEX
from utils.loaders import get_last_updated


def clean_and_aggregate_facilities(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and aggregate generation facilities data.
    Groups by facility and sums capacity while handling missing coordinates.
    """
    # Remove rows with missing essential data
    df_clean = df.dropna(subset=['plant_name', 'capacity_mw', 'fuel'])
    # Handle missing coordinates by using regional approximations
    df_clean['lat'] = df_clean['lat'].fillna(31.0)
    df_clean['lon'] = df_clean['lon'].fillna(-99.0)
    # Group by plant and aggregate
    return df_clean.groupby(['plant_name', 'fuel', 'lat', 'lon']).agg({
        'capacity_mw': 'sum',
        'last_updated': 'first'
    }).reset_index()


def create_fixed_texas_map(df: pd.DataFrame) -> pdk.Deck:
    """
    Create a Texas-focused map similar to ERCOT price maps with realistic facility distribution.
    """
    try:
        if df.empty:
            st.warning("No generation data available for mapping.")
            # Return empty deck for graceful handling
            return pdk.Deck(layers=[], initial_view_state=pdk.ViewState(latitude=31.0, longitude=-99.0, zoom=5.2))

        df = df.copy()

        # Validate required columns
        required_cols = ['fuel', 'capacity_mw', 'lat', 'lon', 'plant_name']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            st.error(f"Missing required columns for map: {missing_cols}")
            return pdk.Deck(layers=[], initial_view_state=pdk.ViewState(latitude=31.0, longitude=-99.0, zoom=5.2))

        # Add colors based on fuel type (similar to ERCOT color coding)
        def get_color(fuel):
            try:
                color_hex = FUEL_COLORS_HEX.get(str(fuel), '#a0a0a0')
                # Convert hex to RGB with good opacity
                color_hex = color_hex.lstrip('#')
                return [int(color_hex[0:2], 16), int(color_hex[2:4], 16), int(color_hex[4:6], 16), 180]
            except (ValueError, IndexError):
                return [160, 160, 160, 180]  # Default gray

        df['color'] = df['fuel'].apply(get_color)

        # ERCOT-style radius scaling based on capacity
        try:
            max_capacity = float(df['capacity_mw'].max())
            min_capacity = float(df['capacity_mw'].min())
        except (ValueError, TypeError):
            max_capacity = min_capacity = 100.0  # Default values

        def ercot_style_radius(capacity):
            """Scale radius similar to ERCOT maps - clearer size differences."""
            try:
                capacity = float(capacity)
                if pd.isna(capacity) or capacity <= 0:
                    return 8  # Default size for invalid capacity
                if max_capacity == min_capacity:
                    return 12

                # Use square root scaling for better visual distinction
                normalized = (capacity - min_capacity) / (max_capacity - min_capacity)

                # ERCOT-style scaling: small plants visible, large plants prominent
                sqrt_scaled = math.sqrt(max(0, min(1, normalized)))
                return 6 + (sqrt_scaled * 25)  # Range: 6-31 pixels
            except (ValueError, TypeError, ZeroDivisionError):
                return 10  # Default radius

        df['radius'] = df['capacity_mw'].apply(ercot_style_radius)

        # Ensure all tooltip fields are strings
        for col in ["plant_name", "fuel", "capacity_mw"]:
            if col in df.columns:
                df[col] = df[col].astype(str)

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
            "ScatterplotLayer",
            data=df,
            get_position=["lon", "lat"],
            get_color="color",
            get_radius="radius",
            radius_scale=1,
            radius_min_pixels=4,
            radius_max_pixels=40,
            pickable=True,
            auto_highlight=True,
            stroked=True,
            filled=True,
            get_line_color=[255, 255, 255, 120],
            line_width_min_pixels=1,
            opacity=0.8,
        )

        # Texas-focused view (similar to ERCOT maps)
        view_state = pdk.ViewState(
            latitude=31.0,           # Texas center
            longitude=-99.0,
            zoom=5.2,                # Lock to a wide Texas view
            pitch=0,
            min_zoom=5.2,            # Lock zoom level
            max_zoom=5.2,
        )

        return pdk.Deck(
            layers=[layer],
            initial_view_state=view_state,
            map_style='mapbox://styles/mapbox/light-v10',  # Clean style like ERCOT
            views=[pdk.View(type='MapView', controller=False)],
            tooltip=tooltip  # type: ignore
        )

    except Exception as e:
        st.error(f"Error creating map: {str(e)}")
        # Return empty deck for graceful error handling
        return pdk.Deck(layers=[], initial_view_state=pdk.ViewState(latitude=31.0, longitude=-99.0, zoom=5.2))


def render_legend_and_counts(df: pd.DataFrame):
    """Render fuel type legend with colors and counts."""
    st.markdown("### Map Legend")
    fuel_counts = df['fuel'].value_counts()
    cols = st.columns(min(5, len(fuel_counts)))
    for i, (fuel, count) in enumerate(fuel_counts.items()):
        color = FUEL_COLORS_HEX.get(str(fuel), '#a0a0a0')
        capacity = df[df['fuel'] == fuel]['capacity_mw'].sum()
        with cols[i % len(cols)]:
            st.markdown(
                f'<div style="display: flex; align-items: center; margin-bottom: 6px;">'
                f'<div style="width: 14px; height: 14px; background-color: {color}; '
                f'border-radius: 50%; margin-right: 10px; border: 1px solid #ddd;"></div>'
                f'<span style="font-size: 14px;"><b>{fuel}</b><br/>{count} plants '
                f'({capacity:,.0f} MW)</span></div>',
                unsafe_allow_html=True
            )
    st.markdown("""
    **Map Guide:**
    - 📏 **Point Size**: Proportional to plant capacity (MW)
    - 📍 **Hover**: View detailed facility information
    - 🎯 **Colors**: Fuel type designation
    """)


def render():
    """Render the Generation Map tab."""

    # Local styles for consistent TAB-branded hero section matching fuel mix
    st.markdown(
        """
        <style>
            .generation-hero .accent-bar {
                height: 6px;
                width: 140px;
                background: linear-gradient(90deg,#1B365D,#C8102E);
                border-radius: 4px;
                margin: 6px 0 18px 0;
            }
            .generation-hero .subtitle {
                color:#0B1939;
                opacity:0.85;
                font-size:0.98rem;
                margin-top:2px;
            }
            .status-pill {
                display:inline-block;
                background:#F5F7FA;
                color:#0B1939;
                border-left:4px solid #1B365D;
                padding:6px 10px;
                border-radius:6px;
                font-size:0.85rem;
                font-weight:600;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Hero section with consistent styling
    st.markdown(
        """
        <div class="generation-hero">
            <h2 style="margin-bottom:4px; color:#1B365D; font-weight:800;">
                Texas Power Generation Facilities
            </h2>
            <div class="accent-bar"></div>
            <div class="subtitle">
                Interactive map of operating power plants across Texas with capacity and fuel type data.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    try:
        # Load generation data with robust error handling
        try:
            data_path = Path(__file__).parent.parent.parent / "data" / "generation.parquet"
            if not data_path.exists():
                st.error("Generation data file not found. Please run the ETL process to generate data.")
                st.info("Run: `python etl/eia_plants_etl.py` to fetch and process generation data.")
                return

            df = pd.read_parquet(data_path)
            if df.empty:
                st.warning("Generation data file is empty. Please regenerate the data.")
                return

        except Exception as e:
            st.error(f"Error loading generation data: {str(e)}")
            st.info("To generate the data, run: python etl/eia_plants_etl.py")
            return

        # Clean and aggregate data with error handling
        try:
            clean_df = clean_and_aggregate_facilities(df)
            if clean_df.empty:
                st.warning("No valid generation facilities found after data cleaning.")
                return
        except Exception as e:
            st.error(f"Error processing generation data: {str(e)}")
            return

        # Data status indicator with consistent styling
        st.markdown(
            f"""
            <div class="status-pill" style="margin-top:10px;">
                ✅ Live Data: EIA Power Plants Database - {len(clean_df)} facilities
                from EIA Operating Generator Capacity API
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Calculate KPIs with error handling
        try:
            total_plants = len(clean_df)
            total_capacity = float(clean_df['capacity_mw'].sum())
            fuel_breakdown = clean_df.groupby('fuel')['capacity_mw'].sum().sort_values(ascending=False)

            if not fuel_breakdown.empty:
                largest_plant = clean_df.loc[clean_df['capacity_mw'].idxmax()]
            else:
                largest_plant = {'plant_name': 'Unknown', 'capacity_mw': 0}

        except Exception as e:
            st.error(f"Error calculating statistics: {str(e)}")
            return
        # Display KPIs using branded metric-card components (hover accents)
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
            display_name = plant_name[:20] + ("..." if len(plant_name) > 20 else "")
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-card-title">Largest Plant</div>
                <div class="metric-card-value" style="font-size: 1.5rem;">{display_name}</div>
                <div class="metric-card-subtitle">{largest_plant['capacity_mw']:,.0f} MW</div>
            </div>
            """, unsafe_allow_html=True)
        # Interactive map - COMPACT HEIGHT
        st.subheader("Interactive Facility Map")
        deck = create_fixed_texas_map(clean_df)
        st.pydeck_chart(deck, height=450)
        # Enhanced legend with fuel colors
        render_legend_and_counts(clean_df)
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
    except FileNotFoundError as e:
        st.error(f"Generation data not available: {e}")
        st.info("To generate the data, run: python etl/eia_plants_etl.py")
    except Exception as e:
        st.error(f"Error loading generation data: {e}")
        st.info("Please ensure the ETL script has been run to generate the data file.")
