"""
EIA Power Plants ETL Script (Stub)

Fetches power generation facility data from EIA's Power Plants dataset.
This stub creates an empty schema file - implementation pending.

Target API: EIA Atlas FeatureServer
URL: https://atlas.eia.gov/datasets/eia::power-plants/
"""

from datetime import datetime
from pathlib import Path
import pandas as pd

# Constants
DATA_DIR = Path(__file__).parent.parent / "data"


def create_empty_schema() -> pd.DataFrame:
    """
    Create empty dataframe with canonical schema.
    
    Expected columns from EIA Power Plants FeatureServer:
    - Plant_Name -> plant_name
    - Latitude -> lat
    - Longitude -> lon
    - Total_MW (or similar) -> capacity_mw
    - PrimSource (primary fuel) -> fuel
    
    Returns:
        Empty DataFrame with correct schema
    """
    return pd.DataFrame(columns=[
        'plant_name',
        'lat',
        'lon',
        'capacity_mw',
        'fuel',
        'last_updated'
    ])


def main():
    """Generate empty schema file."""
    print("Creating empty generation.parquet schema file...")
    
    # Create empty schema
    df = create_empty_schema()
    
    # Ensure data directory exists
    DATA_DIR.mkdir(exist_ok=True, parents=True)
    
    # Write empty parquet with schema
    output_path = DATA_DIR / "generation.parquet"
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
    print("TODO: Implement EIA Power Plants data fetch")
    print("="*60)
    print("\nData Source:")
    print("  - EIA Atlas Power Plants Feature Service")
    print("  - URL: https://atlas.eia.gov/datasets/eia::power-plants/")
    print("  - Format: ArcGIS FeatureServer REST API")
    
    print("\nImplementation Steps:")
    print("  1. Query FeatureServer with geometry filter for Texas")
    print("     (approximate bounds: lat 25.8-36.5, lon -106.6 to -93.5)")
    print("  2. Extract features with attributes:")
    print("     - Plant_Name (facility name)")
    print("     - Latitude, Longitude (location)")
    print("     - Total_MW or Nameplate (capacity)")
    print("     - PrimSource or other fuel field (primary fuel type)")
    print("  3. Filter for operating plants (Status = 'Operating' or similar)")
    print("  4. Transform to canonical schema")
    print("  5. Write to parquet")
    
    print("\nExample FeatureServer Query:")
    print("  GET /rest/services/.../FeatureServer/0/query")
    print("  Params: f=json, where=Status='Operating', outFields=*, geometry=...")
    
    print("\nFuel Type Mapping:")
    print("  - Map EIA fuel codes to canonical types (GAS, WIND, SOLAR, etc.)")
    print("  - Handle multiple fuel types per plant (use primary)")


if __name__ == "__main__":
    main()
