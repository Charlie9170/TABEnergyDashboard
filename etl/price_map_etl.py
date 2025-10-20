"""
Price Map ETL Script (Demo Data)

Creates demo price map data for development and testing.
This stub will be replaced with real ERCOT price data later.

Demo data includes sample nodes across Texas with realistic prices.
"""

from datetime import datetime
from pathlib import Path
import pandas as pd

# Constants
DATA_DIR = Path(__file__).parent.parent / "data"


def create_demo_data() -> pd.DataFrame:
    """
    Create demo price map data with sample nodes.
    
    Returns:
        DataFrame with demo price data
    """
    # Sample nodes across Texas with realistic locations and prices
    demo_data = [
        # North Texas
        {"node_id": "HB_NORTH_1", "lat": 33.0, "lon": -96.8, "price_cperkwh": 4.2, "region": "North"},
        {"node_id": "HB_NORTH_2", "lat": 32.8, "lon": -97.3, "price_cperkwh": 4.5, "region": "North"},
        {"node_id": "HB_NORTH_3", "lat": 32.5, "lon": -96.5, "price_cperkwh": 4.1, "region": "North"},
        
        # Houston
        {"node_id": "HB_HOUSTON_1", "lat": 29.8, "lon": -95.4, "price_cperkwh": 5.2, "region": "Houston"},
        {"node_id": "HB_HOUSTON_2", "lat": 29.6, "lon": -95.2, "price_cperkwh": 5.5, "region": "Houston"},
        {"node_id": "HB_HOUSTON_3", "lat": 30.0, "lon": -95.6, "price_cperkwh": 5.0, "region": "Houston"},
        
        # South Texas
        {"node_id": "HB_SOUTH_1", "lat": 27.8, "lon": -97.4, "price_cperkwh": 3.8, "region": "South"},
        {"node_id": "HB_SOUTH_2", "lat": 26.2, "lon": -98.2, "price_cperkwh": 3.5, "region": "South"},
        
        # West Texas
        {"node_id": "HB_WEST_1", "lat": 31.8, "lon": -102.4, "price_cperkwh": 3.2, "region": "West"},
        {"node_id": "HB_WEST_2", "lat": 32.5, "lon": -101.9, "price_cperkwh": 3.0, "region": "West"},
        
        # Central/Austin
        {"node_id": "HB_AUSTIN_1", "lat": 30.3, "lon": -97.7, "price_cperkwh": 4.8, "region": "Central"},
        {"node_id": "HB_AUSTIN_2", "lat": 30.5, "lon": -97.9, "price_cperkwh": 4.6, "region": "Central"},
    ]
    
    df = pd.DataFrame(demo_data)
    
    # Add last_updated timestamp
    df['last_updated'] = datetime.utcnow().isoformat()
    
    return df


def main():
    """Generate demo price map data."""
    print("Creating demo price map data...")
    
    # Create demo data
    df = create_demo_data()
    
    # Ensure data directory exists
    DATA_DIR.mkdir(exist_ok=True, parents=True)
    
    # Write to parquet
    output_path = DATA_DIR / "price_map.parquet"
    df.to_parquet(
        output_path,
        engine='pyarrow',
        compression='snappy',
        index=False
    )
    
    print(f"✓ Successfully wrote {len(df)} demo records to {output_path}")
    print(f"  Regions: {', '.join(sorted(df['region'].unique()))}")
    print(f"  Price range: ${df['price_cperkwh'].min():.2f} - ${df['price_cperkwh'].max():.2f} ¢/kWh")
    
    # TODO: Replace with real ERCOT data
    print("\nTODO: Implement real ERCOT price data fetch")
    print("  Source: ERCOT CDR (Contour Data Records)")
    print("  URL: https://www.ercot.com/content/cdr/contours/rtmLmp.html")
    print("  Format: Real-time LMP (Locational Marginal Price) data")


if __name__ == "__main__":
    main()
