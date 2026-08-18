#!/usr/bin/env python3
"""
ERCOT GIS (Generator Interconnection Status) Report ETL Script

Replaces the static May 2025 CDR snapshot (see ercot_queue_etl.py, deprecated)
with ERCOT's monthly Generator Interconnection Status report, which is the
actual interconnection queue and is republished every month.

Source discovery (no hardcoded URL — the filename format is not consistently
parseable, e.g. "GIS_Report_July2026.xlsx" vs "GIS_Report_Jun2026.xlsx"):
    1. GET the public JSON listing for ERCOT report type 15933 (GIS Report).
    2. Filter to documents whose FriendlyName starts with "GIS_Report_" (the
       same reportTypeId also serves an unrelated "Co-located Battery
       Identification Report" series).
    3. Take the entry with the maximum PublishDate.
    4. Download it by DocID.

Because step 3 always resolves to "whatever is newest," a month's report not
being published yet is not an error condition — the previous month's report
is simply still the newest, and the pipeline uses it. Only a genuine fetch/
parse failure (site unreachable, no matching documents, unexpected sheet
layout) raises, which leaves data/queue.parquet untouched (this script only
overwrites it after fully parsing and validating in memory).

Parses two sheets — "Project Details - Large Gen" and "Project Details -
Small Gen" — and unions them into the full active queue. The GIS report has
no lat/lon or coordinates of any kind (only County and a free-text POI
substation description), so geocoding reuses the county-centroid + jitter
helper from ercot_queue_etl.py (same limitation the old CDR pipeline had).

Output: data/queue.parquet (unfiltered — the "large" vs "committed" vs "full
queue" views are a rendering concern, handled in app/tabs/queue_tab.py, not
an ETL concern).

Also writes data/queue_gis_metadata.json, a small sidecar with the report's
own published Summary-sheet totals (project count, capacity under study) and
provenance (DocID, publish date, report month). scripts/validate_gis_queue_
parquet.py cross-checks the parsed row count/capacity against these totals
without needing to re-fetch the source file.

Usage:
    python etl/ercot_gis_queue_etl.py
"""

import json
import logging
import os
import sys
from datetime import datetime, UTC
from typing import Optional

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Reuse, do not reimplement: county-centroid + jitter geocoding and the
# atomic-write-with-verification helper both live in the CDR pipeline and
# are source-agnostic.
from ercot_queue_etl import (  # noqa: E402
    get_county_coordinates_for_project,
    atomic_write_parquet,
    ETLProcessingError,
    ETLValidationError,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

GIS_REPORT_TYPE_ID = "15933"
GIS_LISTING_URL = (
    "https://www.ercot.com/misapp/servlets/IceDocListJsonWS"
    f"?reportTypeId={GIS_REPORT_TYPE_ID}"
)
GIS_DOWNLOAD_URL_TMPL = (
    "https://www.ercot.com/misdownload/servlets/mirDownload?doclookupId={doc_id}"
)
GIS_FRIENDLY_NAME_PREFIX = "GIS_Report_"

QUEUE_PARQUET_PATH = "data/queue.parquet"
GIS_METADATA_PATH = "data/queue_gis_metadata.json"

# ERCOT "Fuel Types" legend from the GIS Report's own Acronyms sheet.
# Friendly names are chosen to match app/utils/colors.py's
# get_fuel_color_hex() vocabulary so no color-map changes are needed.
FUEL_CODE_MAP = {
    "BIO": "Biomass",
    "COA": "Coal",
    "GAS": "Natural Gas",
    "GEO": "Geothermal",
    "HYD": "Hydro",
    "NUC": "Nuclear",
    "OIL": "Oil",
    "OTH": "Other",
    "PET": "Petroleum Coke",
    "SOL": "Solar",
    "WAT": "Water",
    "WIN": "Wind",
}

REQUIRED_HEADER_ANCHOR = "INR"


def _build_session() -> requests.Session:
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({"User-Agent": "TAB-Energy-Dashboard/1.0"})
    return session


def discover_latest_gis_report(session: requests.Session) -> dict:
    """
    Find the newest published GIS Report document.

    Not finding *this month's* file is normal (see module docstring) — this
    function always returns whatever is newest, which may be last month's
    report. It only raises if the listing itself is unreachable or contains
    no GIS Report documents at all, which is a real failure.
    """
    logger.info(f"Fetching GIS Report document listing: {GIS_LISTING_URL}")
    response = session.get(GIS_LISTING_URL, timeout=30)
    response.raise_for_status()

    payload = response.json()
    documents = payload.get("ListDocsByRptTypeRes", {}).get("DocumentList", [])
    if not documents:
        raise ETLProcessingError(
            "GIS Report listing endpoint returned no documents at all "
            f"(reportTypeId={GIS_REPORT_TYPE_ID})"
        )

    # The same reportTypeId also serves the unrelated "Co-located Battery
    # Identification Report" — filter to the actual GIS Report by name.
    gis_docs = [
        doc["Document"]
        for doc in documents
        if doc.get("Document", {}).get("FriendlyName", "").startswith(GIS_FRIENDLY_NAME_PREFIX)
    ]
    if not gis_docs:
        raise ETLProcessingError(
            f"No documents with FriendlyName starting '{GIS_FRIENDLY_NAME_PREFIX}' "
            f"found under reportTypeId={GIS_REPORT_TYPE_ID}. The listing contained "
            f"{len(documents)} unrelated documents — ERCOT may have changed the "
            "report naming or moved it to a different reportTypeId."
        )

    latest = max(gis_docs, key=lambda d: d["PublishDate"])
    logger.info(
        f"Latest GIS Report: {latest['FriendlyName']} "
        f"(DocID={latest['DocID']}, published {latest['PublishDate']})"
    )
    return latest


def download_gis_report(doc: dict, session: requests.Session, dest_path: str) -> None:
    url = GIS_DOWNLOAD_URL_TMPL.format(doc_id=doc["DocID"])
    logger.info(f"Downloading {doc['FriendlyName']} from {url}")
    response = session.get(url, timeout=60)
    response.raise_for_status()

    content = response.content
    if len(content) < 1000 or not content[:2] == b"PK":
        # xlsx files are zip archives (PK magic bytes); a tiny or non-zip
        # response means we got an error page, not a spreadsheet.
        raise ETLProcessingError(
            f"Downloaded GIS Report does not look like a valid .xlsx file "
            f"({len(content)} bytes)"
        )

    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    with open(dest_path, "wb") as f:
        f.write(content)
    logger.info(f"Saved GIS Report to {dest_path} ({len(content):,} bytes)")


def _find_header_row(raw: pd.DataFrame, anchor: str = REQUIRED_HEADER_ANCHOR, max_scan: int = 60) -> int:
    """
    Scan the first column for the header row, rather than hardcoding a
    skiprows count — the notes/title block above the header has varied in
    length between report months in the past (see ercot_queue_etl.py, which
    does the same kind of scan for the CDR file).
    """
    limit = min(max_scan, len(raw))
    for i in range(limit):
        first_cell = raw.iloc[i, 0]
        if isinstance(first_cell, str) and first_cell.strip() == anchor:
            return i
    raise ETLProcessingError(
        f"Could not find header row (first column == '{anchor}') in first {limit} rows"
    )


def _map_fuel(fuel_code: str, technology_code: str) -> Optional[str]:
    """
    Map ERCOT's coded Fuel (+Technology) to the friendly names
    get_fuel_color_hex() understands. Must run the storage special case
    BEFORE the generic map: battery storage is reported as Fuel=OTH,
    Technology=BA, not as its own fuel code — a naive Fuel-only map would
    mislabel it as "Other" (and it's the single largest technology bucket
    in the queue, so this is not an edge case).
    """
    fuel_code = (fuel_code or "").strip().upper()
    technology_code = (technology_code or "").strip().upper()

    if fuel_code == "OTH" and technology_code == "BA":
        return "Battery Storage"

    return FUEL_CODE_MAP.get(fuel_code)  # None if unmapped — validator catches this


def _derive_status(gim_study_phase: str) -> str:
    """
    Bucket the free-text GIM Study Phase into the 3-stage enum approved for
    this pipeline, with Interconnection Agreement signing as the key
    distinguishing milestone (checked first, regardless of FIS state):

      - "Interconnection Agreement Signed": phase ends in "IA" (not "No IA")
      - "Early Stage": Screening Study itself still in progress
      - "Under Study": everything else (SS complete, no IA yet)
    """
    if not isinstance(gim_study_phase, str) or not gim_study_phase.strip():
        return "Under Study"

    phase = gim_study_phase.strip()
    if phase.endswith("IA") and not phase.endswith("No IA"):
        return "Interconnection Agreement Signed"
    if phase.startswith("SS Started"):
        return "Early Stage"
    return "Under Study"


def _parse_project_sheet(xlsx_path: str, sheet_name: str, size_category: str) -> pd.DataFrame:
    raw = pd.read_excel(xlsx_path, sheet_name=sheet_name, header=None, nrows=60)
    header_idx = _find_header_row(raw)

    df = pd.read_excel(xlsx_path, sheet_name=sheet_name, header=header_idx)
    df = df.dropna(subset=["INR"]).copy()

    has_study_phase = "GIM Study Phase" in df.columns

    out = pd.DataFrame()
    out["project_name"] = df["Project Name"].fillna("Unknown Project")
    out["fuel_code"] = df["Fuel"].astype(str).str.strip().str.upper()
    out["technology"] = df["Technology"].astype(str).str.strip().str.upper()
    out["fuel_type"] = [
        _map_fuel(f, t) for f, t in zip(out["fuel_code"], out["technology"])
    ]
    out["capacity_mw"] = pd.to_numeric(df["Capacity (MW)"], errors="coerce")
    out["county"] = df["County"].fillna("Unknown County")
    out["poi_location"] = df.get("POI Location", pd.Series(dtype=object)).fillna("")
    out["interconnecting_entity"] = df.get("Interconnecting Entity", pd.Series(dtype=object)).fillna("")
    out["cdr_reporting_zone"] = df.get("CDR Reporting Zone", pd.Series(dtype=object)).fillna("")
    out["projected_cod"] = pd.to_datetime(df.get("Projected COD"), errors="coerce").dt.strftime("%Y-%m-%d")
    if has_study_phase:
        out["gim_study_phase"] = df["GIM Study Phase"].fillna("")
        out["status"] = out["gim_study_phase"].apply(_derive_status)
    else:
        # Small Gen has no "GIM Study Phase" column — small generators
        # (<=10 MW) skip the Screening Study / FIS stages Large Gen goes
        # through, so "Early Stage"/"Under Study" don't apply. The sheet's
        # own "IA Signed" date column is the only milestone it reports;
        # describe it honestly rather than borrowing Large Gen's SS/FIS
        # vocabulary for a process this sheet doesn't actually go through.
        ia_signed_col = df.get("IA Signed")
        has_ia = ia_signed_col.notna() if ia_signed_col is not None else pd.Series(False, index=df.index)
        out["gim_study_phase"] = has_ia.map({
            True: "Small Generator — Interconnection Agreement signed",
            False: "Small Generator — no Interconnection Agreement on file",
        })
        out["status"] = has_ia.map({
            True: "Interconnection Agreement Signed",
            False: "Under Study",
        })
    out["ia_signed"] = out["status"] == "Interconnection Agreement Signed"
    out["size_category"] = size_category

    return out


def parse_gis_report(xlsx_path: str) -> pd.DataFrame:
    logger.info(f"Parsing GIS Report from {xlsx_path}")

    large = _parse_project_sheet(xlsx_path, "Project Details - Large Gen", "Large")
    logger.info(f"Parsed {len(large)} projects from Project Details - Large Gen")

    small = _parse_project_sheet(xlsx_path, "Project Details - Small Gen", "Small")
    logger.info(f"Parsed {len(small)} projects from Project Details - Small Gen")

    combined = pd.concat([large, small], ignore_index=True)
    if combined.empty:
        raise ETLProcessingError("No projects parsed from either Large Gen or Small Gen sheet")

    # Geocode via county centroid + jitter (reused, not reimplemented).
    coords = [
        get_county_coordinates_for_project(row.project_name, row.county, row.fuel_type or "Unknown")
        for row in combined.itertuples()
    ]
    combined["lat"] = [c[0] for c in coords]
    combined["lon"] = [c[1] for c in coords]

    combined["data_source"] = "ERCOT GIS Report"
    combined["last_updated"] = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

    logger.info(
        f"Combined queue: {len(combined)} projects, "
        f"{combined['capacity_mw'].sum():,.0f} MW total"
    )
    logger.info(f"Status distribution: {combined['status'].value_counts().to_dict()}")
    unmapped = combined[combined["fuel_type"].isna()]
    if not unmapped.empty:
        codes = sorted(unmapped["fuel_code"].unique().tolist())
        logger.warning(f"{len(unmapped)} rows have unmapped fuel codes: {codes}")

    return combined


def parse_summary_totals(xlsx_path: str) -> dict:
    """
    Pull ERCOT's own published totals from the Summary sheet, used as an
    independent cross-check by scripts/validate_gis_queue_parquet.py. These
    are free-form text/number rows, not a clean table, so this is a small
    targeted scan rather than a header-based read.
    """
    raw = pd.read_excel(xlsx_path, sheet_name="Summary", header=None, nrows=40)

    total_requests = None
    total_capacity_mw = None
    for i in range(len(raw)):
        row = raw.iloc[i].tolist()
        for j, cell in enumerate(row):
            if not isinstance(cell, str):
                continue
            if cell.strip() == "Total Interconnection Requests" and j + 1 < len(row):
                total_requests = row[j + 1]
            if cell.strip() == "Total Capacity Under Study" and j + 1 < len(row):
                total_capacity_mw = row[j + 1]

    if total_requests is None or total_capacity_mw is None:
        raise ETLProcessingError(
            "Could not find 'Total Interconnection Requests' / "
            "'Total Capacity Under Study' in the Summary sheet — "
            "ERCOT may have changed the report layout"
        )

    return {
        "source_total_interconnection_requests": int(total_requests),
        "source_total_capacity_mw": float(total_capacity_mw),
    }


def write_metadata(doc: dict, summary_totals: dict, path: str) -> None:
    metadata = {
        "report_friendly_name": doc["FriendlyName"],
        "report_doc_id": doc["DocID"],
        "report_publish_date": doc["PublishDate"],
        "fetched_at": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
        **summary_totals,
    }
    with open(path, "w") as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"Wrote GIS report metadata to {path}: {metadata}")


def main() -> bool:
    logger.info("=" * 60)
    logger.info("STARTING ERCOT GIS INTERCONNECTION QUEUE ETL")
    logger.info("=" * 60)

    try:
        session = _build_session()
        doc = discover_latest_gis_report(session)

        raw_xlsx_path = f"data/.gis_report_raw_{doc['DocID']}.xlsx"
        download_gis_report(doc, session, raw_xlsx_path)

        queue_df = parse_gis_report(raw_xlsx_path)
        summary_totals = parse_summary_totals(raw_xlsx_path)

        # Fully parsed and cross-checked in memory before anything on disk
        # is overwritten — a failure above this point leaves the previous
        # data/queue.parquet untouched.
        atomic_write_parquet(queue_df, QUEUE_PARQUET_PATH)
        write_metadata(
            doc,
            {
                **summary_totals,
                "parsed_public_detail_rows": int(len(queue_df)),
                "parsed_public_capacity_mw": float(queue_df["capacity_mw"].sum()),
            },
            GIS_METADATA_PATH,
        )

        os.remove(raw_xlsx_path)

        logger.info("=" * 60)
        logger.info("ERCOT GIS QUEUE ETL COMPLETED SUCCESSFULLY")
        logger.info(f"Report: {doc['FriendlyName']} (published {doc['PublishDate']})")
        logger.info(f"Projects: {len(queue_df)}, Total capacity: {queue_df['capacity_mw'].sum():,.0f} MW")
        logger.info("=" * 60)
        return True

    except (ETLValidationError, ETLProcessingError) as e:
        logger.error(f"ETL process failed: {e}")
        return False
    except requests.RequestException as e:
        logger.error(f"Network error fetching GIS Report: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in ETL process: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
