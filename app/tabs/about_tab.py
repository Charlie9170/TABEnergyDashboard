"""
About & Data Sources Tab

Public methodology and source notes for TAB members and policymakers.
"""

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

import sys
sys.path.append(str(Path(__file__).parent.parent))

from utils.data_sources import DATA_SOURCES
from utils.loaders import get_data_path


def get_file_timestamp(filename: str) -> str:
    """Last modified time of a committed data file, or 'Not available'."""
    try:
        file_path = get_data_path(filename)
        if file_path.exists():
            timestamp = datetime.fromtimestamp(file_path.stat().st_mtime)
            return timestamp.strftime("%B %d, %Y at %I:%M %p CT")
        return "Not available"
    except Exception:
        return "Not available"


def _generation_period_label() -> str:
    """EIA-923 window from generation.parquet, if present."""
    try:
        path = get_data_path("generation.parquet")
        if not path.exists():
            return ""
        df = pd.read_parquet(path, columns=["generation_period_start", "generation_period_end"])
        if df.empty:
            return ""
        start = df["generation_period_start"].iloc[0]
        end = df["generation_period_end"].iloc[0]
        if pd.isna(start) or pd.isna(end):
            return ""
        return f"{start} to {end}"
    except Exception:
        return ""


def _queue_report_label() -> str:
    """GIS report name and publish date from queue_gis_metadata.json."""
    meta_path = Path(__file__).parent.parent.parent / "data" / "queue_gis_metadata.json"
    if not meta_path.exists():
        return ""
    try:
        meta = json.loads(meta_path.read_text())
        name = meta.get("report_friendly_name", "")
        published = str(meta.get("report_publish_date", ""))[:10]
        if name and published:
            return f"{name} (published {published})"
        return str(name)
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return ""


def _source_card(title: str, dataset_key: str, parquet_name: str, extra_lines: list[str]) -> None:
    info = DATA_SOURCES[dataset_key]
    extras = "".join(f"<strong>{label}:</strong> {value}<br>" for label, value in extra_lines if value)
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-card-title">{title}</div>
            <div style="margin-top: 0.5rem; font-size: 0.9rem; color: #64748B;">
                <strong>Source:</strong> {info['source']}<br>
                <strong>Dataset:</strong> {info.get('dataset', info.get('api', ''))}<br>
                <strong>Coverage:</strong> {info.get('coverage', '')}<br>
                {extras}
                <strong>Dashboard file updated:</strong> {get_file_timestamp(parquet_name)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render():
    """Render the About & Data Sources tab."""

    st.markdown("### About & Data Sources")
    st.markdown(
        "This dashboard provides the Texas Association of Business with current, "
        "publicly sourced information on the Texas electricity market and related "
        "energy infrastructure for policy discussion."
    )

    st.markdown("## Data Sources & Methodology")
    st.markdown(
        "Each data tab is refreshed from official public sources on a scheduled "
        "dashboard cycle. The source reporting period is not always the same as "
        "the dashboard refresh time."
    )

    col1, col2 = st.columns(2)

    with col1:
        _source_card(
            "ERCOT Fuel Mix",
            "fuelmix",
            "fuelmix.parquet",
            [("Update cadence", DATA_SOURCES["fuelmix"]["update_frequency"])],
        )
        st.markdown("")
        _source_card(
            "Interconnection Queue",
            "queue",
            "queue.parquet",
            [
                ("Current report", _queue_report_label()),
                ("Update cadence", DATA_SOURCES["queue"]["update_frequency"]),
            ],
        )
        st.markdown("")
        _source_card(
            "Minerals & Critical Minerals",
            "minerals",
            "minerals_deposits.parquet",
            [("Update cadence", DATA_SOURCES["minerals"]["update_frequency"])],
        )

    with col2:
        _source_card(
            "Real-Time Price Map",
            "price_map",
            "price_map.parquet",
            [("Update cadence", DATA_SOURCES["price_map"]["update_frequency"])],
        )
        st.markdown("")
        _source_card(
            "Generation Facilities",
            "generation",
            "generation.parquet",
            [
                ("Reported generation period", _generation_period_label()),
                ("Update cadence", DATA_SOURCES["generation"]["update_frequency"]),
            ],
        )

    with st.expander("Methodology & Limitations"):
        st.markdown("""
        **Fuel mix.** Hourly EIA generation by fuel type for ERCOT (respondent ERCO),
        covering approximately the last seven days. This is grid-level generation, not plant-level output.

        **Price map.** A snapshot of ERCOT real-time settlement point prices at 15 published
        locations (9 major hubs and 6 strategic nodes). The source page updates frequently;
        this dashboard stores the latest interval captured by the scheduled ETL.

        **Generation.** Nameplate capacity and measured EIA-923 facility-fuel output for Texas
        plants. Reported generation is a multi-month average for the latest EIA window with data,
        not real-time output. Plants without measured EIA-923 data are excluded.

        **Interconnection queue.** Public Large Gen and Small Gen detail sheets from ERCOT's
        Generator Interconnection Status (GIS) Report. A signed interconnection agreement is a
        study-process milestone, not a construction guarantee. ERCOT's Summary sheet can list
        more requests than appear on the public detail sheets.

        **Minerals.** A manually compiled set of publicly disclosed Texas deposits. It is not
        an automated feed and is not complete statewide coverage.

        Processing is limited to formatting, aggregation, geocoding for display, and validation.
        Underlying source values are not altered for advocacy purposes.
        """)

    st.markdown("## Credits")
    st.markdown(
        "Developed by Charlie LaMair for the Texas Association of Business, "
        "supporting energy policy research and data analysis."
    )
    st.markdown(
        "Texas Association of Business · "
        "[texasbusiness.com](https://www.texasbusiness.com) · "
        "info@txbiz.org · (512) 477-6721"
    )
    st.caption(
        f"Page loaded {datetime.now().strftime('%B %d, %Y at %I:%M %p CT')}."
    )
