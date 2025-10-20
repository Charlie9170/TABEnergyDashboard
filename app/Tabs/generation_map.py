"""TX Generation Map Tab - Displays power generation facilities across Texas."""

import streamlit as st
import pydeck as pdk
import pandas as pd

def render_generation_map_tab():
    """Render the TX Generation Map tab with demo data."""
    st.header("Texas Generation Facilities Map")
    st.markdown("Major power generation facilities across Texas (Demo Data)")
    
    # Demo data: Major power plants in Texas with different fuel types
    demo_data = pd.DataFrame({
        'name': ['South Texas Nuclear', 'W.A. Parish', 'Martin Lake', 'Limestone', 
                 'Comanche Peak', 'Big Brown', 'Coleto Creek', 'Sandow',
                 'Sam Rayburn Wind', 'Horse Hollow Wind', 'Buckthorn Solar', 'Roadrunner Solar'],
        'lat': [28.7951, 29.4864, 32.5200, 31.5200, 
                32.2926, 32.2500, 28.8700, 30.5500,
                33.6200, 32.3800, 30.1500, 29.2800],
        'lon': [-96.0492, -95.6386, -94.5700, -96.5800, 
                -97.7851, -96.1400, -97.2500, -96.9800,
                -100.4500, -100.2400, -102.3200, -100.5400],
        'fuel_type': ['Nuclear', 'Natural Gas', 'Coal', 'Coal',
                      'Nuclear', 'Coal', 'Coal', 'Coal',
                      'Wind', 'Wind', 'Solar', 'Solar'],
        'capacity_mw': [2700, 3653, 2250, 1720,
                        2430, 1190, 630, 590,
                        457, 735, 180, 497],
    })
    
    # Color mapping by fuel type
    fuel_colors = {
        'Nuclear': [156, 89, 182],
        'Natural Gas': [52, 152, 219],
        'Coal': [44, 62, 80],
        'Wind': [39, 174, 96],
        'Solar': [243, 156, 18],
    }
    
    demo_data['color'] = demo_data['fuel_type'].map(fuel_colors)
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Facilities", len(demo_data))
    with col2:
        st.metric("Total Capacity", f"{demo_data['capacity_mw'].sum():,.0f} MW")
    with col3:
        st.metric("Renewable", f"{demo_data[demo_data['fuel_type'].isin(['Wind', 'Solar'])]['capacity_mw'].sum():,.0f} MW")
    with col4:
        pct_renewable = (demo_data[demo_data['fuel_type'].isin(['Wind', 'Solar'])]['capacity_mw'].sum() / 
                        demo_data['capacity_mw'].sum() * 100)
        st.metric("Renewable %", f"{pct_renewable:.1f}%")
    
    # Filter by fuel type
    fuel_types = ['All'] + sorted(demo_data['fuel_type'].unique().tolist())
    selected_fuel = st.selectbox("Filter by Fuel Type", fuel_types)
    
    if selected_fuel != 'All':
        filtered_data = demo_data[demo_data['fuel_type'] == selected_fuel]
    else:
        filtered_data = demo_data
    
    # Create pydeck map
    view_state = pdk.ViewState(
        latitude=31.0,
        longitude=-99.0,
        zoom=5.5,
        pitch=40,
    )
    
    # Create layer with generation facilities
    layer = pdk.Layer(
        'ColumnLayer',
        data=filtered_data,
        get_position='[lon, lat]',
        get_elevation='capacity_mw * 10',
        elevation_scale=50,
        radius=15000,
        get_fill_color='color',
        pickable=True,
        auto_highlight=True,
    )
    
    # Tooltip
    tooltip = {
        "html": "<b>{name}</b><br/>Type: {fuel_type}<br/>Capacity: {capacity_mw} MW",
        "style": {
            "backgroundColor": "steelblue",
            "color": "white"
        }
    }
    
    # Render the map
    r = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip=tooltip,
        map_style='mapbox://styles/mapbox/dark-v10',
    )
    
    st.pydeck_chart(r)
    
    # Legend
    st.subheader("Fuel Type Legend")
    legend_cols = st.columns(len(fuel_colors))
    for idx, (fuel, color) in enumerate(fuel_colors.items()):
        with legend_cols[idx]:
            st.markdown(f"<span style='color:rgb({color[0]},{color[1]},{color[2]})'>⬤</span> {fuel}", 
                       unsafe_allow_html=True)
    
    # Show data table
    st.subheader("Generation Facilities")
    display_df = filtered_data[['name', 'fuel_type', 'capacity_mw']].sort_values('capacity_mw', ascending=False)
    display_df.columns = ['Facility', 'Fuel Type', 'Capacity (MW)']
    st.dataframe(display_df, use_container_width=True)
    
    st.info("Note: This tab displays demo data. Integration with actual ERCOT generation facility data is planned.")
