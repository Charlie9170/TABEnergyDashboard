"""ERCOT Queue Tab - Displays interconnection queue data."""

import streamlit as st
import plotly.express as px
import pandas as pd

def render_ercot_queue_tab():
    """Render the ERCOT Queue tab with demo data."""
    st.header("ERCOT Interconnection Queue")
    st.markdown("Projects in the ERCOT interconnection queue (Demo Data)")
    
    # Demo data: Sample projects in various stages
    demo_data = pd.DataFrame({
        'project_name': [
            'West Texas Solar Farm', 'Gulf Coast Wind Farm', 'Central Texas Battery Storage',
            'Panhandle Wind II', 'Houston Solar Complex', 'Corpus Christi Gas Plant',
            'Hill Country Wind', 'East Texas Solar', 'Dallas Battery Storage',
            'Rio Grande Solar', 'Lubbock Wind Farm', 'Austin Battery'
        ],
        'fuel_type': ['Solar', 'Wind', 'Battery', 'Wind', 'Solar', 'Natural Gas',
                      'Wind', 'Solar', 'Battery', 'Solar', 'Wind', 'Battery'],
        'capacity_mw': [250, 400, 150, 350, 200, 500, 300, 180, 100, 220, 380, 120],
        'status': ['Engineering', 'Engineering', 'Construction', 'Planning', 'Engineering', 'Planning',
                   'Construction', 'Engineering', 'Planning', 'Engineering', 'Construction', 'Planning'],
        'queue_date': pd.to_datetime([
            '2023-01-15', '2023-02-20', '2022-11-10', '2023-03-05', '2023-01-28',
            '2022-12-15', '2022-10-20', '2023-02-14', '2023-03-10', '2023-01-05',
            '2022-09-30', '2023-02-25'
        ]),
        'expected_cod': pd.to_datetime([
            '2025-06-01', '2025-12-01', '2024-09-01', '2026-01-01', '2025-08-01',
            '2026-03-01', '2024-11-01', '2025-09-01', '2026-02-01', '2025-07-01',
            '2024-10-01', '2026-01-15'
        ]),
    })
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Projects", len(demo_data))
    with col2:
        st.metric("Total Capacity", f"{demo_data['capacity_mw'].sum():,.0f} MW")
    with col3:
        renewable_capacity = demo_data[demo_data['fuel_type'].isin(['Wind', 'Solar', 'Battery'])]['capacity_mw'].sum()
        st.metric("Renewable+Storage", f"{renewable_capacity:,.0f} MW")
    with col4:
        pct_renewable = (renewable_capacity / demo_data['capacity_mw'].sum() * 100)
        st.metric("Renewable %", f"{pct_renewable:.1f}%")
    
    # Filters
    col1, col2 = st.columns(2)
    with col1:
        fuel_filter = st.multiselect(
            "Filter by Fuel Type",
            options=sorted(demo_data['fuel_type'].unique()),
            default=sorted(demo_data['fuel_type'].unique())
        )
    with col2:
        status_filter = st.multiselect(
            "Filter by Status",
            options=sorted(demo_data['status'].unique()),
            default=sorted(demo_data['status'].unique())
        )
    
    # Apply filters
    filtered_data = demo_data[
        (demo_data['fuel_type'].isin(fuel_filter)) &
        (demo_data['status'].isin(status_filter))
    ]
    
    # Chart: Capacity by Fuel Type
    st.subheader("Capacity by Fuel Type")
    fuel_summary = filtered_data.groupby('fuel_type')['capacity_mw'].sum().reset_index()
    fuel_summary = fuel_summary.sort_values('capacity_mw', ascending=False)
    
    fig = px.bar(
        fuel_summary,
        x='fuel_type',
        y='capacity_mw',
        labels={'fuel_type': 'Fuel Type', 'capacity_mw': 'Capacity (MW)'},
        template='plotly_dark'
    )
    fig.update_layout(showlegend=False, height=400)
    st.plotly_chart(fig, use_container_width=True)
    
    # Chart: Capacity by Status
    st.subheader("Capacity by Status")
    status_summary = filtered_data.groupby('status')['capacity_mw'].sum().reset_index()
    
    fig2 = px.pie(
        status_summary,
        values='capacity_mw',
        names='status',
        template='plotly_dark'
    )
    fig2.update_layout(height=400)
    st.plotly_chart(fig2, use_container_width=True)
    
    # Timeline view
    st.subheader("Expected Commercial Operation Dates")
    timeline_data = filtered_data.sort_values('expected_cod')
    
    fig3 = px.timeline(
        timeline_data,
        x_start='queue_date',
        x_end='expected_cod',
        y='project_name',
        color='fuel_type',
        labels={'project_name': 'Project', 'fuel_type': 'Fuel Type'},
        template='plotly_dark'
    )
    fig3.update_layout(height=400, showlegend=True)
    st.plotly_chart(fig3, use_container_width=True)
    
    # Show data table
    st.subheader("Queue Projects")
    display_df = filtered_data[['project_name', 'fuel_type', 'capacity_mw', 'status', 'queue_date', 'expected_cod']].sort_values('queue_date', ascending=False)
    display_df.columns = ['Project', 'Fuel Type', 'Capacity (MW)', 'Status', 'Queue Date', 'Expected COD']
    display_df['Queue Date'] = display_df['Queue Date'].dt.strftime('%Y-%m-%d')
    display_df['Expected COD'] = display_df['Expected COD'].dt.strftime('%Y-%m-%d')
    st.dataframe(display_df, use_container_width=True)
    
    st.info("Note: This tab displays demo data. Integration with actual ERCOT queue data is planned.")
