"""
Validate queue.parquet after the ERCOT GIS Queue ETL.

Modeled on validate_generation_parquet.py: runs with no continue-on-error in
CI, after the ETL step and before the commit step. A failure here means the
job fails before `git add`, so main's last-committed queue.parquet is left
untouched — this script never touches the file, only reads it.
"""

import json
import sys
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent.parent / "data"
QUEUE_PATH = DATA_DIR / "queue.parquet"
METADATA_PATH = DATA_DIR / "queue_gis_metadata.json"

REQUIRED_COLUMNS = [
    "project_name", "lat", "lon", "capacity_mw", "fuel_type",
    "county", "status", "last_updated",
]

ALLOWED_STATUSES = {"Early Stage", "Under Study", "Interconnection Agreement Signed"}

TEXAS_LAT_BOUNDS = (25.8, 36.5)
TEXAS_LON_BOUNDS = (-106.7, -93.5)

# Real-world tolerance, not a bug budget: the Summary sheet's own totals
# ("currently tracking") and our Large+Small union have historically differed
# by a few percent even on a known-good parse (observed ~4% on the July 2026
# file), most likely due to timing/scope differences between how ERCOT
# generates the Summary tallies vs. the detail sheets. This tolerance is wide
# enough to absorb that normal drift while still catching a real breakage —
# e.g. a header-row miss that silently drops most of a sheet would be off by
# far more than 15%.
CROSS_CHECK_TOLERANCE = 0.15


def fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    sys.exit(1)


def main() -> None:
    if not QUEUE_PATH.exists():
        fail(f"missing {QUEUE_PATH}")

    df = pd.read_parquet(QUEUE_PATH)
    print(f"queue.parquet: {len(df)} rows, columns={list(df.columns)}")

    if len(df) == 0:
        fail("queue.parquet is empty")

    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        fail(f"missing required columns: {missing_cols}")

    # --- Non-null checks (capacity may be zero/negative — repowering net-
    # change projects are legitimate, see ercot_gis_queue_etl.py — but every
    # row must have a value at all) ---
    for col in ["project_name", "capacity_mw", "fuel_type", "county", "status", "lat", "lon"]:
        n_null = df[col].isna().sum()
        if n_null > 0:
            fail(f"{n_null} rows have null {col}")

    if not pd.api.types.is_numeric_dtype(df["capacity_mw"]):
        fail("capacity_mw must be numeric")

    # --- Fuel mapping completeness: a null/unmapped fuel_type would have
    # already tripped the null check above, since ercot_gis_queue_etl.py
    # leaves unmapped fuel codes as NaN specifically so this check catches
    # them (rather than silently bucketing under "Other"). Also assert the
    # raw fuel_code column, if present, has no leftover blanks. ---
    if "fuel_code" in df.columns:
        blank_codes = df["fuel_code"].isin(["", "NAN", "NONE"]).sum()
        if blank_codes > 0:
            fail(f"{blank_codes} rows have a blank/invalid raw fuel_code")

    # --- Status enum: exactly the 3 approved buckets, and they must sum to
    # the total row count with no rows dropped or double-counted. ---
    bad_status = set(df["status"].unique()) - ALLOWED_STATUSES
    if bad_status:
        fail(f"status contains values outside the approved enum: {bad_status}")

    status_counts = df["status"].value_counts()
    print("Status distribution:")
    for status in ["Early Stage", "Under Study", "Interconnection Agreement Signed"]:
        print(f"  {status}: {status_counts.get(status, 0)}")
    if status_counts.sum() != len(df):
        fail(
            f"status bucket counts ({status_counts.sum()}) don't sum to "
            f"total row count ({len(df)})"
        )

    # --- Texas coordinate bounds ---
    out_of_bounds = (
        (df["lat"] < TEXAS_LAT_BOUNDS[0]) | (df["lat"] > TEXAS_LAT_BOUNDS[1]) |
        (df["lon"] < TEXAS_LON_BOUNDS[0]) | (df["lon"] > TEXAS_LON_BOUNDS[1])
    )
    if out_of_bounds.any():
        fail(f"{out_of_bounds.sum()} rows have coordinates outside Texas bounds")

    # --- Cross-check against the source report's own published totals ---
    if not METADATA_PATH.exists():
        fail(f"missing {METADATA_PATH} (written by ercot_gis_queue_etl.py alongside queue.parquet)")

    metadata = json.loads(METADATA_PATH.read_text())
    for key in ("source_total_interconnection_requests", "source_total_capacity_mw"):
        if key not in metadata:
            fail(f"{METADATA_PATH} missing '{key}'")

    source_count = metadata["source_total_interconnection_requests"]
    source_mw = metadata["source_total_capacity_mw"]
    parsed_count = len(df)
    parsed_mw = df["capacity_mw"].sum()

    count_diff = abs(parsed_count - source_count) / source_count
    if count_diff > CROSS_CHECK_TOLERANCE:
        fail(
            f"parsed row count {parsed_count} differs from source's own "
            f"'Total Interconnection Requests' ({source_count}) by "
            f"{count_diff:.1%}, exceeding {CROSS_CHECK_TOLERANCE:.0%} tolerance"
        )

    mw_diff = abs(parsed_mw - source_mw) / source_mw
    if mw_diff > CROSS_CHECK_TOLERANCE:
        fail(
            f"parsed total capacity {parsed_mw:,.0f} MW differs from source's "
            f"'Total Capacity Under Study' ({source_mw:,.0f} MW) by "
            f"{mw_diff:.1%}, exceeding {CROSS_CHECK_TOLERANCE:.0%} tolerance"
        )

    print(
        f"Cross-check OK: {parsed_count} rows vs source {source_count} "
        f"({count_diff:.1%} diff), {parsed_mw:,.0f} MW vs source {source_mw:,.0f} MW "
        f"({mw_diff:.1%} diff)"
    )

    print(f"OK: queue.parquet passed GIS queue validation ({len(df)} rows, {parsed_mw:,.0f} MW)")
    sys.exit(0)


if __name__ == "__main__":
    main()
