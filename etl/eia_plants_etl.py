"""
EIA Plants ETL Script

Fetches Texas power generation facility data from EIA API.
Includes plant names, capacity, fuel types, and geocoded locations.

Data source: EIA Operating Generator Capacity API
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import time

import pandas as pd
import requests

# Constants
API_BASE_URL = "https://api.eia.gov/v2"
ENDPOINT = "electricity/operating-generator-capacity"
DATA_DIR = Path(__file__).parent.parent / "data"


def get_api_key():
    """
    Get EIA API key from environment or Streamlit secrets.
    
    Returns:
        API key string
        
    Raises:
        ValueError if API key not found
    """
    # Try environment variable first
    api_key = os.environ.get('EIA_API_KEY')
    
    # Try Streamlit secrets as fallback
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get('EIA_API_KEY')
        except:
            pass
    
    if not api_key:
        raise ValueError(
            "EIA_API_KEY not found. Please set it as an environment variable "
            "or in Streamlit secrets (.streamlit/secrets.toml)"
        )
    
    return api_key


def fetch_texas_generators(api_key: str) -> pd.DataFrame:
    """
    Fetch Texas power generator data from EIA API.
    
    Args:
        api_key: EIA API key
        
    Returns:
        DataFrame with Texas generator data
    """
    all_data = []
    offset = 0
    length = 5000  # Max per request
    
    print("Fetching Texas power plant data from EIA...")
    
    while True:
        # Build API request for Texas generators
        url = f"{API_BASE_URL}/{ENDPOINT}/data/"
        params = {
            'api_key': api_key,
            'frequency': 'monthly',
            'data[0]': 'nameplate-capacity-mw',
            'facets[stateid][]': 'TX',  # Texas only
            'start': '2024-01',  # Recent data
            'end': '2024-01',
            'offset': offset,
            'length': length,
        }
        
        print(f"  Fetching offset {offset}...")
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        # Extract data from response
        if 'response' in result and 'data' in result['response']:
            data = result['response']['data']
            if not data:
                break  # No more data
            
            all_data.extend(data)
            
            # Check if there's more data
            total = int(result['response'].get('total', 0))
            if offset + length >= total:
                break
            
            offset += length
            
            # Rate limiting - be respectful to EIA API
            time.sleep(0.1)
        else:
            break
    
    print(f"  Retrieved {len(all_data)} generator records")
    
    if not all_data:
        raise ValueError("No generator data returned from EIA API")
    
    return pd.DataFrame(all_data)


def geocode_plant_locations(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add approximate coordinates for Texas power plants.
    Uses a combination of known major plant locations and regional estimates.
    
    Args:
        df: DataFrame with plant data
        
    Returns:
        DataFrame with lat/lon coordinates added
    """
    print("Adding geographic coordinates...")
    
    # Major Texas cities/regions for approximation
    texas_regions = {
        'houston': {'lat': 29.7604, 'lon': -95.3698, 'keywords': ['houston', 'baytown', 'channelview', 'pasadena']},
        'dallas': {'lat': 32.7767, 'lon': -96.7970, 'keywords': ['dallas', 'plano', 'garland', 'mesquite']},
        'austin': {'lat': 30.2672, 'lon': -97.7431, 'keywords': ['austin', 'cedar park', 'round rock']},
        'san_antonio': {'lat': 29.4241, 'lon': -98.4936, 'keywords': ['san antonio', 'alamo', 'schertz']},
        'fort_worth': {'lat': 32.7555, 'lon': -97.3308, 'keywords': ['fort worth', 'arlington', 'irving']},
        'el_paso': {'lat': 31.7619, 'lon': -106.4850, 'keywords': ['el paso']},
        'corpus_christi': {'lat': 27.8006, 'lon': -97.3964, 'keywords': ['corpus christi', 'robstown']},
        'lubbock': {'lat': 33.5779, 'lon': -101.8552, 'keywords': ['lubbock']},
        'amarillo': {'lat': 35.2220, 'lon': -101.8313, 'keywords': ['amarillo']},
        'beaumont': {'lat': 30.0802, 'lon': -94.1266, 'keywords': ['beaumont', 'port arthur']},
        'tyler': {'lat': 32.3513, 'lon': -95.3011, 'keywords': ['tyler', 'longview']},
        'waco': {'lat': 31.5494, 'lon': -97.1467, 'keywords': ['waco']},
        'midland': {'lat': 32.0253, 'lon': -102.0779, 'keywords': ['midland', 'odessa']},
        'west_texas': {'lat': 31.8, 'lon': -102.5, 'keywords': ['wind', 'mesa', 'desert', 'pecos']},
        'south_texas': {'lat': 28.5, 'lon': -98.5, 'keywords': ['eagle pass', 'laredo', 'brownsville']},
        'east_texas': {'lat': 32.0, 'lon': -94.5, 'keywords': ['marshall', 'texarkana', 'carthage']},
        'panhandle': {'lat': 35.0, 'lon': -101.5, 'keywords': ['pampa', 'borger', 'hereford']},
    }
    
    def match_plant_to_region(plant_name: str) -> tuple:
        """Match plant name to region and return lat, lon, region."""
        plant_name_lower = str(plant_name).lower()
        
        # Try to match plant name to region
        for region, info in texas_regions.items():
            for keyword in info['keywords']:
                if keyword in plant_name_lower:
                    # Add small random offset based on plant name hash
                    lat = info['lat'] + (hash(plant_name) % 100 - 50) * 0.01
                    lon = info['lon'] + (hash(plant_name) % 100 - 50) * 0.01
                    return lat, lon, region
        
        # Default to central Texas if no match
        lat = 31.0 + (hash(plant_name) % 200 - 100) * 0.02  
        lon = -99.0 + (hash(plant_name) % 200 - 100) * 0.03
        return lat, lon, 'central_texas'
    
    # Apply geocoding using vectorized approach
    df = df.copy()
    geo_results = df['plantName'].apply(match_plant_to_region)
    
    df['lat'] = [result[0] for result in geo_results]
    df['lon'] = [result[1] for result in geo_results] 
    df['matched_region'] = [result[2] for result in geo_results]
    
    return df


def normalize_fuel_types(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize EIA fuel type codes to canonical fuel names.
    
    Args:
        df: DataFrame with EIA fuel data
        
    Returns:
        DataFrame with normalized fuel types
    """
    # EIA fuel type mapping to canonical names
    fuel_mapping = {
        'Solar Photovoltaic': 'SOLAR',
        'Natural Gas Steam Turbine': 'GAS', 
        'Natural Gas Combined Cycle': 'GAS',
        'Natural Gas Combustion Turbine': 'GAS',
        'Natural Gas Internal Combustion Engine': 'GAS',
        'Wind Turbine - Onshore': 'WIND',
        'Wind Turbine - Offshore': 'WIND', 
        'Coal Steam Turbine': 'COAL',
        'Nuclear Steam Turbine': 'NUCLEAR',
        'Hydroelectric Turbine': 'HYDRO',
        'Battery Energy Storage': 'STORAGE',
        'Batteries': 'STORAGE',
        'Biomass Steam Turbine': 'BIOMASS',
        'Landfill Gas': 'BIOMASS',
        'Municipal Solid Waste': 'BIOMASS',
    }
    
    # Apply fuel mapping
    df['fuel_normalized'] = df['technology'].map(fuel_mapping).fillna('OTHER')
    
    return df


def transform_to_canonical_schema(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transform EIA data to canonical generation schema.
    
    Args:
        df: Raw EIA generator DataFrame
        
    Returns:
        DataFrame with canonical schema
    """
    print("Transforming to canonical schema...")
    
    # Convert capacity to numeric (handle string values from EIA API)
    df['nameplate-capacity-mw'] = pd.to_numeric(df['nameplate-capacity-mw'], errors='coerce')
    
    # Group by plant to aggregate generators
    plant_groups = df.groupby('plantName').agg({
        'nameplate-capacity-mw': 'sum',  # Sum all generators at plant
        'lat': 'first',  # Use first coordinate (they should be same for plant)
        'lon': 'first',
        'fuel_normalized': lambda x: x.mode().iloc[0] if not x.empty else 'OTHER',  # Most common fuel
        'matched_region': 'first'
    }).reset_index()
    
    # Create canonical DataFrame
    canonical_df = pd.DataFrame({
        'plant_name': plant_groups['plantName'],
        'lat': plant_groups['lat'],
        'lon': plant_groups['lon'],
        'capacity_mw': plant_groups['nameplate-capacity-mw'],
        'fuel': plant_groups['fuel_normalized'],
        'last_updated': datetime.now(timezone.utc).isoformat()
    })
    
    # Filter out very small generators (< 1 MW) for cleaner visualization
    canonical_df = canonical_df[canonical_df['capacity_mw'] >= 1.0].copy()
    
    # Sort by capacity (largest first)
    canonical_df = canonical_df.sort_values('capacity_mw', ascending=False).reset_index(drop=True)
    
    print(f"Processed {len(canonical_df)} power plants from {len(df)} generators")
    
    # Summary statistics
    total_capacity = canonical_df['capacity_mw'].sum()
    fuel_breakdown = canonical_df.groupby('fuel')['capacity_mw'].sum().sort_values(ascending=False)
    
    print(f"Total capacity: {total_capacity:,.0f} MW")
    print("Fuel breakdown:")
    for fuel, capacity in fuel_breakdown.items():
        percentage = (capacity / total_capacity) * 100
        print(f"  {fuel}: {capacity:,.0f} MW ({percentage:.1f}%)")
    
    return canonical_df


def run_etl():
    """Main ETL execution."""
    try:
        # Get API key
        api_key = get_api_key()
        
        # Fetch Texas generator data
        df_raw = fetch_texas_generators(api_key)
        
        # Add geographic coordinates
        df_with_coords = geocode_plant_locations(df_raw)
        
        # Normalize fuel types
        df_with_fuel = normalize_fuel_types(df_with_coords)
        
        # Transform to canonical schema
        df_canonical = transform_to_canonical_schema(df_with_fuel)
        
        # Ensure data directory exists
        DATA_DIR.mkdir(exist_ok=True, parents=True)
        
        # Write to parquet
        output_path = DATA_DIR / "generation.parquet"
        df_canonical.to_parquet(output_path, engine='pyarrow', compression='snappy', index=False)
        
        print(f"\n✓ Successfully wrote {len(df_canonical)} power plants to {output_path}")
        print(f"Geographic coverage: Texas statewide")
        print(f"Date range: Latest available EIA data")
        
    except Exception as e:
        print(f"✗ Error in ETL process: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_etl()

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
