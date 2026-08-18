"""
Validate generation.parquet after EIA Plants ETL.

Ensures measured (non-fabricated) data before CI commits to main.
"""

import sys
from pathlib import Path

import pandas as pd

DATA_PATH = Path(__file__).parent.parent / "data" / "generation.parquet"

PARISH_LAT = 29.48
PARISH_LON = -95.63
COORD_TOLERANCE = 0.05
FABRICATED_RATIO = 0.7
RATIO_TOLERANCE = 0.001


def main() -> None:
    if not DATA_PATH.exists():
        print(f"FAIL: missing {DATA_PATH}")
        sys.exit(1)

    df = pd.read_parquet(DATA_PATH)
    print(f"generation.parquet: {len(df)} rows, columns={list(df.columns)}")

    if len(df) == 0:
        print("FAIL: generation.parquet is empty")
        sys.exit(1)

    if "actual_generation_mw" not in df.columns:
        print("FAIL: missing actual_generation_mw column")
        sys.exit(1)

    if "generation_is_estimated" not in df.columns:
        print("FAIL: missing generation_is_estimated column")
        sys.exit(1)

    if df["generation_is_estimated"].any():
        print("FAIL: generation_is_estimated contains True values")
        sys.exit(1)

    ratio = df["actual_generation_mw"] / df["capacity_mw"]
    fabricated = (ratio - FABRICATED_RATIO).abs() < RATIO_TOLERANCE
    if fabricated.any():
        n = fabricated.sum()
        print(f"FAIL: {n} rows match fabricated 70% capacity factor ratio")
        sys.exit(1)

    parish = df[df["plant_name"].str.contains("W A Parish", case=False, na=False)]
    if parish.empty:
        print("FAIL: W A Parish not found in generation.parquet")
        sys.exit(1)

    row = parish.iloc[0]
    if abs(row.lat - PARISH_LAT) > COORD_TOLERANCE or abs(row.lon - PARISH_LON) > COORD_TOLERANCE:
        print(
            f"FAIL: W A Parish coords ({row.lat:.4f}, {row.lon:.4f}) "
            f"expected ~({PARISH_LAT}, {PARISH_LON})"
        )
        sys.exit(1)

    if abs(row.actual_generation_mw - row.capacity_mw * FABRICATED_RATIO) < 1.0:
        print(f"FAIL: W A Parish generation {row.actual_generation_mw} looks fabricated")
        sys.exit(1)

    print("OK: generation.parquet passed measured-data validation")
    sys.exit(0)


if __name__ == "__main__":
    main()
