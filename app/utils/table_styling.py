"""
Professional table styling utilities for TAB Energy Dashboard

Provides consistent, reusable table styling across the application
with TAB design system colors and professional formatting.
"""

# Professional table styling for Pandas DataFrames
# Follows TAB design system with proper spacing, borders, and typography
PROFESSIONAL_TABLE_STYLE = {
    'properties': {
        'text-align': 'left',
        'font-family': '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
        'font-size': '13px',
        'padding': '8px 12px'
    },
    'table_styles': [
        {
            'selector': 'th',
            'props': [
                ('background-color', '#f8f9fa'),
                ('color', '#374151'),
                ('font-weight', '600'),
                ('text-align', 'left'),
                ('padding', '12px'),
                ('border-bottom', '2px solid #e5e7eb')
            ]
        },
        {
            'selector': 'tr:nth-child(even)',
            'props': [('background-color', '#f9fafb')]
        },
        {
            'selector': 'tr:hover',
            'props': [('background-color', '#f3f4f6')]
        },
        {
            'selector': 'td',
            'props': [('border-bottom', '1px solid #e5e7eb')]
        }
    ]
}


def apply_professional_table_style(styler):
    """
    Apply professional table styling to a Pandas Styler object.
    
    Args:
        styler: pandas.io.formats.style.Styler object
        
    Returns:
        Styled Styler object with professional formatting
        
    Example:
        >>> df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
        >>> styled = apply_professional_table_style(df.style)
        >>> st.dataframe(styled, use_container_width=True)
    """
    return styler.set_properties(**PROFESSIONAL_TABLE_STYLE['properties']).set_table_styles(
        PROFESSIONAL_TABLE_STYLE['table_styles']
    )
