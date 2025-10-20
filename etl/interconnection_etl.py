"""
ERCOT Interconnection Queue ETL Script (Stub)

Fetches proposed generation projects from ERCOT interconnection queue.
This stub creates an empty schema file - implementation pending.

Target Source: interconnection.fyi or ERCOT public reports
URL: https://www.interconnection.fyi/?market=ERCOT
"""

from datetime import datetime
from pathlib import Path
import pandas as pd

# Constants
DATA_DIR = Path(__file__).parent.parent / "data"


def create_empty_schema() -> pd.DataFrame:
    """
    Create empty dataframe with canonical schema.
    
    Expected data from interconnection queue:
    - Project name/ID
    - Location (coordinates)
    - Proposed capacity
    - Fuel/technology type
    - Queue status (study phase, approved, etc.)
    
    Returns:
        Empty DataFrame with correct schema
    """
    return pd.DataFrame(columns=[
        'project_name',
        'lat',
        'lon',
        'proposed_mw',
        'fuel',
        'status',
        'last_updated'
    ])


def main():
    """Generate empty schema file."""
    print("Creating empty queue.parquet schema file...")
    
    # Create empty schema
    df = create_empty_schema()
    
    # Ensure data directory exists
    DATA_DIR.mkdir(exist_ok=True, parents=True)
    
    # Write empty parquet with schema
    output_path = DATA_DIR / "queue.parquet"
    df.to_parquet(
        output_path,
        engine='pyarrow',
        compression='snappy',
        index=False
    )
    
    print(f"✓ Successfully created empty schema at {output_path}")
    print(f"  Schema: {list(df.columns)}")
    
    # Implementation notes
    print("\n" + "="*60)
    print("TODO: Implement ERCOT Interconnection Queue data fetch")
    print("="*60)
    
    print("\nData Source Options:")
    print("  1. interconnection.fyi API/scrape")
    print("     - URL: https://www.interconnection.fyi/?market=ERCOT")
    print("     - May have JSON API or require scraping")
    print("     - Aggregated data across ISOs")
    
    print("\n  2. ERCOT Public Reports")
    print("     - URL: https://www.ercot.com/gridinfo/generation")
    print("     - Format: Excel/CSV downloads")
    print("     - Most authoritative but may need manual updates")
    
    print("\n  3. EIA Form 860 (if available)")
    print("     - Planned generators data")
    print("     - Updated annually")
    
    print("\nImplementation Steps:")
    print("  1. Determine best data source and access method")
    print("  2. Fetch queue data (API call or file download)")
    print("  3. Parse project records with:")
    print("     - Project identifier and name")
    print("     - County/location -> geocode to lat/lon")
    print("     - Proposed capacity (MW)")
    print("     - Technology/fuel type")
    print("     - Queue position/status")
    print("  4. Geocode locations if not provided")
    print("  5. Standardize fuel types to canonical names")
    print("  6. Transform to schema and write parquet")
    
    print("\nStatus Categories (typical):")
    print("  - Screening Study")
    print("  - Feasibility Study")
    print("  - System Impact Study")
    print("  - Facilities Study")
    print("  - IA Pending (Interconnection Agreement)")
    print("  - IA Executed")
    print("  - Withdrawn")


if __name__ == "__main__":
    main()
