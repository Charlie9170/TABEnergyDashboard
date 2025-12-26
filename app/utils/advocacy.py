"""
Advocacy Messages for TAB Energy Dashboard

Policy advocacy messages for each tab, drawn from TAB's energy policy platform.
These messages communicate TAB's pro-business, pro-Texas energy policy positions.
"""

import streamlit as st
import html


def render_advocacy_message(tab_name: str):
    """
    Render a professional advocacy message box for the specified tab.
    
    Args:
        tab_name: Name of the tab ('fuelmix', 'pricemap', 'generation', 'queue', 'minerals')
    """
    messages = {
        'fuelmix': {
            'title': 'TAB Energy Policy: Reliable & Diverse Grid',
            'content': """
            **Texas Association of Business supports a reliable, diverse energy portfolio that keeps 
            electricity affordable for Texas businesses and families.** We advocate for market-based 
            solutions that encourage innovation while maintaining grid reliability. A balanced fuel mix—
            including natural gas, wind, solar, and dispatchable generation—ensures Texas businesses 
            have the dependable, competitively-priced electricity they need to grow and compete globally.
            """
        },
        'pricemap': {
            'title': 'TAB Energy Policy: Competitive Energy Markets',
            'content': """
            **Texas Association of Business champions competitive electricity markets that deliver 
            transparent pricing and consumer choice.** ERCOT's competitive wholesale market has driven 
            innovation and efficiency, keeping Texas electricity costs below the national average. 
            We support policies that maintain market integrity, protect against manipulation, and 
            ensure businesses have access to real-time market information for strategic energy management.
            """
        },
        'generation': {
            'title': 'TAB Energy Policy: Diverse Generation Resources',
            'content': """
            **Texas Association of Business advocates for an "all of the above" energy strategy that 
            leverages Texas' diverse natural resources.** Our state's abundant natural gas, world-class 
            wind and solar resources, and existing coal and nuclear facilities provide reliability and 
            resilience. We support policies that encourage investment in all generation types while 
            allowing market forces to determine the optimal energy mix for Texas businesses and consumers.
            """
        },
        'queue': {
            'title': 'TAB Energy Policy: Infrastructure & Investment',
            'content': """
            **Texas Association of Business supports streamlined, predictable processes for energy 
            infrastructure development.** The interconnection queue represents billions in private 
            investment and thousands of jobs for Texans. We advocate for efficient project review, 
            clear timelines, and policies that reduce regulatory barriers while maintaining safety 
            and reliability standards. Texas businesses need robust energy infrastructure to power 
            continued economic growth.
            """
        },
        'minerals': {
            'title': 'TAB Energy Policy: Critical Minerals & Supply Chain Security',
            'content': """
            **Texas Association of Business champions domestic critical mineral development to strengthen 
            supply chain security for energy technologies.** Rare earth elements and critical minerals 
            are essential for batteries, wind turbines, solar panels, and electric vehicles. We support 
            policies that streamline permitting for responsible mineral extraction, processing, and 
            manufacturing in Texas—reducing dependence on foreign sources while creating high-paying 
            jobs and supporting our energy transition with American-made materials.
            """
        }
    }
    
    message = messages.get(tab_name)
    if not message:
        return
    
    # Escape HTML in title and content to prevent XSS
    safe_title = html.escape(message['title'])
    safe_content = html.escape(message['content'])
    
    # Render as professional info box with TAB branding
    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, #1B365D 0%, #2C4F7C 100%);
            color: #FFFFFF;
            padding: 16px 20px;
            border-radius: 8px;
            border-left: 4px solid #C8102E;
            margin: 12px 0 16px 0;
            box-shadow: 0 2px 8px rgba(27, 54, 93, 0.15);
        ">
            <div style="
                font-size: 14px;
                font-weight: 700;
                margin-bottom: 8px;
                color: #FFFFFF;
                letter-spacing: 0.3px;
            ">
                🏛️ {safe_title}
            </div>
            <div style="
                font-size: 13px;
                line-height: 1.6;
                color: #E8EAED;
                white-space: pre-wrap;
            ">
                {safe_content}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
