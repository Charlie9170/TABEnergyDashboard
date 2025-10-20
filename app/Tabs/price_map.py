"""ERCOT Price Map Tab - Displays geographic electricity price data."""

import streamlit as st
import pydeck as pdk
import pandas as pd

def render_price_map_tab():
    """Render the ERCOT Price Map tab with demo data."""
    st.header("ERCOT Price Map")
    st.markdown("Geographic distribution of electricity prices across Texas (Demo Data)")
    
    # Demo data: Major Texas cities with sample price data
    demo_data = pd.DataFrame({
        'city': ['Houston', 'Dallas', 'Austin', 'San Antonio', 'Fort Worth', 
                 'El Paso', 'Arlington', 'Corpus Christi', 'Plano', 'Laredo'],
        'lat': [29.7604, 32.7767, 30.2672, 29.4241, 32.7555, 
                31.7619, 32.7357, 27.8006, 33.0198, 27.5306],
        'lon': [-95.3698, -96.7970, -97.7431, -98.4936, -97.3308, 
                -106.4850, -97.1081, -97.3964, -96.6989, -99.4803],
        'price_per_mwh': [45.5, 48.2, 46.8, 44.9, 47.5, 
                          52.3, 47.8, 43.2, 48.9, 41.5],
    })
    
    # Display metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Average Price", f"${demo_data['price_per_mwh'].mean():.2f}/MWh")
    with col2:
        st.metric("Lowest Price", f"${demo_data['price_per_mwh'].min():.2f}/MWh")
    with col3:
        st.metric("Highest Price", f"${demo_data['price_per_mwh'].max():.2f}/MWh")
    
    # Create pydeck map
    view_state = pdk.ViewState(
        latitude=31.0,
        longitude=-99.0,
        zoom=5.5,
        pitch=0,
    )
    
    # Create layer with price data
    layer = pdk.Layer(
        'ScatterplotLayer',
        data=demo_data,
        get_position='[lon, lat]',
        get_color='[200, 30, 0, 160]',
        get_radius='price_per_mwh * 500',
        radius_scale=6,
        radius_min_pixels=5,
        radius_max_pixels=50,
        pickable=True,
    )
    
    # Tooltip
    tooltip = {
        "html": "<b>{city}</b><br/>Price: ${price_per_mwh}/MWh",
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
    
    # Show data table
    st.subheader("Price Data by Location")
    display_df = demo_data[['city', 'price_per_mwh']].sort_values('price_per_mwh', ascending=False)
    display_df.columns = ['City', 'Price ($/MWh)']
    st.dataframe(display_df, use_container_width=True)
    
    st.info("Note: This tab displays demo data. Integration with real-time ERCOT price data is planned.")
