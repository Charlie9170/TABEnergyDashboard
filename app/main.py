"""
Texas Association of Business Energy Dashboard

A professional Streamlit application for the Texas Association of Business (TAB)
providing real-time energy market intelligence for policymakers and member companies.

Features:
- Real-time fuel mix from EIA
- ERCOT interconnection queue analysis
- Power generation facilities mapping
- Energy market data visualization

Data sources: U.S. EIA, ERCOT CDR Reports
Updated automatically via robust ETL processes.
"""

import streamlit as st
from pathlib import Path

# Configure Plotly with TAB Design System
try:
    import plotly.io as pio
    import plotly.graph_objects as go

    # Create custom TAB-branded Plotly template
    tab_template = go.layout.Template()
    tab_template.layout = dict(
        font=dict(family="Inter, sans-serif", size=12, color="#0F172A"),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        colorway=["#1B365D", "#C8102E", "#F59E0B", "#3B82F6", "#059669", "#7C3AED", "#0EA5E9"],
        hovermode="closest",
        hoverlabel=dict(bgcolor="white", font_size=12, font_family="Inter"),
        title=dict(font=dict(size=18, color="#1B365D", family="Inter"), x=0.05, xanchor="left"),
        xaxis=dict(
            gridcolor="#E2E8F0",
            gridwidth=1,
            linecolor="#E2E8F0",
            showgrid=True,
            zeroline=False,
            tickfont=dict(size=11, color="#64748B")
        ),
        yaxis=dict(
            gridcolor="#E2E8F0",
            gridwidth=1,
            linecolor="#E2E8F0",
            showgrid=True,
            zeroline=False,
            tickfont=dict(size=11, color="#64748B")
        ),
        legend=dict(
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="#E2E8F0",
            borderwidth=1,
            font=dict(size=11, color="#64748B")
        ),
        margin=dict(l=60, r=40, t=80, b=60)
    )

    pio.templates["tab_theme"] = tab_template
    pio.templates.default = "tab_theme"
except Exception:
    pass

# Altair theming is optional; skip to avoid version-specific typing issues.

# Import tab modules
from tabs import fuelmix_tab, price_map_tab, generation_tab, queue_tab
from utils.data_sources import render_dashboard_disclaimer

# Page configuration
st.set_page_config(
    page_title="Texas Association of Business - Energy Dashboard",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# Load Professional TAB Design System
def load_custom_css():
    """Load custom CSS from .streamlit/custom.css for unified design system"""
    css_path = Path(__file__).parent.parent / ".streamlit" / "custom.css"
    if css_path.exists():
        with open(css_path, 'r') as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)


load_custom_css()


# Additional TAB Brand Styling - Enhancing base design system
st.markdown("""
<style>
    /* TAB Official Colors: Navy Blue #1B365D, Red #C8102E, White #FFFFFF */

    /* Global compact layout - more zoomed out */
    .main .block-container {
        background-color: #FFFFFF;
        padding-top: 0rem;
        padding-bottom: 1rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 1400px;
    }
    
    /* Reduce overall spacing */
    .element-container {
        margin-bottom: 0.5rem;
    }
    
    /* Compact sections */
    section.main > div {
        padding-top: 0.5rem;
    }

    /* Navigation bar like txbiznews.com */
    .top-nav {
        background-color: #1B365D;
        padding: 0.5rem 2rem;
        margin: -1rem -2rem 0 -2rem;
        color: #FFFFFF;
        text-align: center;
        font-size: 0.875rem;
        font-weight: 500;
        letter-spacing: 0.5px;
    }

    /* Main header matching txbiznews style - COMPACT VERSION */
    .main-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1rem 0 0.75rem 0;
        border-bottom: 3px solid #1B365D;
        margin-bottom: 1rem;
    }

    .header-content {
        flex: 1;
    }

    .main-title {
        color: #1B365D;
        font-size: 1.75rem;
        font-weight: 700;
        margin: 0;
        line-height: 1.1;
    }

    .main-subtitle {
        color: #C8102E;
        font-size: 0.85rem;
        margin: 0.25rem 0 0 0;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .header-logo {
        margin-left: 1.5rem;
    }
    
    .header-logo img {
        border: none !important;
        outline: none !important;
        box-shadow: none !important;
        height: 48px !important;
    }

    .header-logo:focus, .header-logo img:focus {
        outline: none !important;
        border: none !important;
        box-shadow: none !important;
    }

    /* Clean professional tabs - COMPACT */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
        background-color: transparent;
        padding: 0;
        border-bottom: none;
        justify-content: center;
        margin-bottom: 0.5rem;
    }

    .stTabs [data-baseweb="tab"] {
        background-color: #F8F9FA;
        color: #6C757D;
        border: 1px solid #DEE2E6;
        border-radius: 6px 6px 0 0;
        padding: 8px 16px;
        font-weight: 500;
        font-size: 0.9rem;
        transition: all 0.2s ease;
        margin-right: 2px;
    }
    
    .stTabs [data-baseweb="tab-panel"] {
        padding-top: 0.75rem;
    }

    .stTabs [aria-selected="true"] {
        background-color: #1B365D;
        color: #FFFFFF;
        border-color: #1B365D;
        font-weight: 600;
    }

    .stTabs [data-baseweb="tab"]:hover {
        background-color: #E9ECEF;
        color: #1B365D;
    }

    /* Professional KPI cards - COMPACT */
    .metric-card {
        background: #FFFFFF;
        border: 2px solid #E9ECEF;
        border-radius: 8px;
        padding: 1rem 1.25rem;
        text-align: center;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }

    .metric-card:hover {
        border-color: #C8102E;
        box-shadow: 0 8px 25px rgba(0,0,0,0.1);
        transform: translateY(-2px);
    }

    .metric-card-title {
        font-size: 0.75rem;
        color: #6C757D;
        margin: 0 0 0.4rem 0;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .metric-card-value {
        font-size: 2rem;
        font-weight: 700;
        color: #1B365D;
        margin: 0;
        line-height: 1;
    }

    .metric-card-subtitle {
        font-size: 0.75rem;
        color: #6C757D;
        margin: 0.3rem 0 0 0;
        font-weight: 400;
    }

    .metric-value {
        font-size: 2.25rem;
        font-weight: 700;
        color: #1B365D;
        margin: 0;
        line-height: 1;
    }

    .metric-label {
        font-size: 0.875rem;
        color: #6C757D;
        margin: 0.5rem 0 0 0;
        font-weight: 500;
    }

    /* Professional status indicators */
    .status-indicator {
        display: inline-flex;
        align-items: center;
        background: #F8F9FA;
        border: 1px solid #DEE2E6;
        border-radius: 20px;
        padding: 8px 16px;
        font-size: 0.85rem;
        font-weight: 600;
        color: #495057;
        margin-bottom: 1rem;
    }

    .status-indicator.live {
        background: linear-gradient(135deg, #C8102E 0%, #DC3545 100%);
        color: #FFFFFF;
        border-color: #C8102E;
    }

    .status-dot {
        width: 8px;
        height: 8px;
        background-color: #28A745;
        border-radius: 50%;
        margin-right: 8px;
        animation: pulse 2s infinite;
    }

    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.5; }
        100% { opacity: 1; }
    }

    /* Clean section headers - COMPACT */
    .section-header {
        color: #1B365D;
        font-size: 1.4rem;
        font-weight: 600;
        margin: 1.25rem 0 0.75rem 0;
        padding-bottom: 0.4rem;
        border-bottom: 2px solid #E9ECEF;
    }

    /* Professional buttons */
    .stButton > button {
        background: linear-gradient(135deg, #1B365D 0%, #2C4F7C 100%);
        color: #FFFFFF;
        border: none;
        border-radius: 8px;
        padding: 12px 24px;
        font-weight: 500;
        font-size: 0.9rem;
        transition: all 0.3s ease;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .stButton > button:hover {
        background: linear-gradient(135deg, #0F172A 0%, #1B365D 100%);
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(27, 54, 93, 0.3);
    }

    /* Professional headings */
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 {
        color: #1B365D;
        font-weight: 600;
    }

    /* Footer matching txbiznews style - COMPACT */
    .footer-section {
        background: #F8F9FA;
        border-top: 3px solid #1B365D;
        padding: 1.5rem 2rem;
        margin: 2rem -1rem -1rem -1rem;
        text-align: center;
    }

    .footer-branding {
        color: #1B365D;
        font-size: 0.95rem;
        font-weight: 600;
        margin-bottom: 0.3rem;
    }

    .footer-tagline {
        color: #C8102E;
        font-size: 0.85rem;
        font-weight: 500;
        margin-bottom: 0.5rem;
    }

    .footer-details {
        color: #6C757D;
        font-size: 0.75rem;
        line-height: 1.5;
    }

    /* Hide default Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# Professional Header matching txbiznews.com
st.markdown("""
<div class="top-nav">
    Pro Business, Pro Texas | Powered by the Texas Association of Business
</div>
""", unsafe_allow_html=True)

st.markdown(
    """
<div class="main-header">
    <div class="header-content">
        <h1 class="main-title">Texas Energy Dashboard</h1>
        <p class="main-subtitle">Real-time Energy Market Intelligence</p>
    </div>
    <div class="header-logo">
        <img src="https://media.licdn.com/dms/image/v2/C560BAQEIzBAjOjBfNQ/company-logo_200_200/company-logo_200_200/0/1630593527551/texas_association_of_business_logo?e=2147483647&v=beta&t=i1boFi5ZKSQUjuRoNy78BBOYMKoMYK8YHEFP9Lzqs-g"
             alt="TAB Logo" style="height:48px; object-fit:contain; border:none; outline:none; box-shadow:none;" />
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# Tab navigation using Streamlit tabs
tab1, tab2, tab3, tab4 = st.tabs(["Fuel Mix", "Price Map", "Generation Map", "Interconnection Queue"])

with tab1:
    fuelmix_tab.render()

with tab2:
    price_map_tab.render()

with tab3:
    generation_tab.render()

with tab4:
    queue_tab.render()

# Global dashboard disclaimer and status
render_dashboard_disclaimer()

# Professional Footer matching txbiznews.com
st.markdown("""
<div class="footer-section">
    <div class="footer-branding">Powered by Texas Association of Business</div>
    <div class="footer-tagline">Pro Business, Pro Texas | The Texas State Chamber</div>
    <div class="footer-details">
        Professional Energy Market Intelligence<br>
        Data Sources: U.S. EIA, ERCOT CDR Reports | Updated via automated ETL processes<br>
        © 2025 Texas Association of Business. All rights reserved.
    </div>
</div>
""", unsafe_allow_html=True)
