"""
Data source tracking and citation utilities.

Provides consistent data source citations across all dashboard tabs.
"""

from typing import Any, Optional
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

# Every writer (ETL scripts, CI) stores timestamps in UTC. Display is Central
# Time because the audience is Texas; ZoneInfo handles CST/CDT so the offset is
# never hardcoded.
CENTRAL_TZ = ZoneInfo("America/Chicago")

# Data source registry - tracks status of each dataset
DATA_SOURCES = {
    'fuelmix': {
        'status': 'live',
        'source': 'U.S. Energy Information Administration (EIA)',
        'dataset': 'RTO fuel-type data (ERCOT)',
        'api': 'EIA v2 electricity/rto/fuel-type-data',
        'respondent': 'ERCO (ERCOT)',
        'coverage': 'Hourly ERCOT generation by fuel type (rolling 7 days)',
        'update_frequency': 'Dashboard ETL every 6 hours',
        'url': 'https://www.eia.gov/opendata/',
    },
    'price_map': {
        'status': 'live',
        'source': 'Electric Reliability Council of Texas (ERCOT)',
        'dataset': 'Real-Time Settlement Point Prices',
        'api': 'Real-Time Settlement Point Prices (SPP)',
        'coverage': '15 settlement points (9 major hubs + 6 strategic nodes)',
        'update_frequency': 'Source updates about every 5 minutes; dashboard ETL every 6 hours',
        'url': 'https://www.ercot.com/mp/data-products/data-product-details?id=NP6-785-ER',
    },
    'generation': {
        'status': 'live',
        'source': 'U.S. Energy Information Administration (EIA)',
        'dataset': 'Operating generator capacity and EIA-923 facility-fuel',
        'api': 'EIA v2 operating-generator-capacity + facility-fuel',
        'coverage': 'Texas plants ≥1 MW with measured EIA-923 generation',
        'update_frequency': 'Dashboard ETL every 6 hours; EIA publications are periodic',
        'url': 'https://www.eia.gov/opendata/',
    },
    'queue': {
        'status': 'live',
        'source': 'Electric Reliability Council of Texas (ERCOT)',
        'dataset': 'Generator Interconnection Status (GIS) Report',
        'api': 'ERCOT Generator Interconnection Status (GIS) Report',
        'coverage': 'Public Large Gen and Small Gen detail sheets',
        'update_frequency': 'ERCOT republishes monthly; dashboard ETL checks every 6 hours',
        'url': 'https://www.ercot.com/mp/data-products/data-product-details?id=PG7-200-ER',
    },
    'minerals': {
        'status': 'live',
        'source': 'Compiled from public geological surveys and industry disclosures',
        'dataset': 'Texas mineral deposits (manually curated)',
        'api': 'Texas General Land Office, USGS, industry disclosures',
        'coverage': 'Selected REE and critical-mineral deposits in Texas',
        'update_frequency': 'Manual; not an automated feed',
        'url': 'https://www.glo.texas.gov/',
        'public_note': 'Not comparable in freshness or completeness to EIA or ERCOT automated feeds.',
        'note': 'Data compiled from GLO reports, USGS surveys, and industry announcements'
    }
}

def format_ct(value: Any) -> str:
    """
    Render a stored UTC timestamp in Central Time, labeled "CT".

    Conversion happens at display time only — stored values stay UTC. Naive
    inputs are read as UTC, which is what every ETL writes. Values that are not
    timestamps at all (e.g. "Unknown") pass through unchanged.
    """
    if value is None or value == "":
        return "Unavailable"

    moment = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(moment):
        return str(value)

    central = moment.tz_convert(CENTRAL_TZ)
    return f"{central.strftime('%b %d, %Y')} {central.strftime('%I:%M %p').lstrip('0')} CT"


def render_freshness_banner(label: str, timestamp: Any, *, meaning: str = "refreshed") -> None:
    """
    Prominent freshness indicator (green status box).

    `meaning` separates the two things a timestamp can mean: "refreshed" is when
    this dashboard last pulled the data, "vintage" is how current the source data
    itself is. They are usually hours apart, so they cannot share one label.
    """
    prefix = "Data through" if meaning == "vintage" else "Last refreshed"
    st.success(f"**{label}** — {prefix}: {format_ct(timestamp)}")


def render_data_source_footer(
    dataset: str,
    last_updated: Optional[str] = None,
    *,
    data_through: Optional[str] = None,
) -> None:
    """
    Compact source / freshness line for the bottom of a data tab.

    Distinguishes the underlying source period (`data_through`) from the
    dashboard ETL write time (`last_updated`).
    """
    if dataset not in DATA_SOURCES:
        st.error(f"Unknown dataset: {dataset}")
        return

    source_info = DATA_SOURCES[dataset]
    status = source_info['status']

    st.markdown("---")

    if status == 'live':
        dataset_label = source_info.get('dataset') or source_info.get('api', '')
        lines = [f"Source: {source_info['source']} · {dataset_label}"]
        if data_through:
            lines.append(f"Data through: {data_through}")
        if last_updated:
            lines.append(f"Last refreshed: {format_ct(last_updated)}")
        note = source_info.get('public_note')
        if note:
            lines.append(note)
        st.caption("  \n".join(lines))
