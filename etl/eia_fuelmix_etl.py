"""
EIA Fuel Mix ETL Script

Fetches hourly electricity generation data by fuel type from the EIA API.
Data source: EIA v2 electricity/rto/fuel-type-data endpoint
Respondent: ERCO (ERCOT)
Time range: Last 7 days

This script:
1. Reads EIA_API_KEY from environment or Streamlit secrets
2. Calls EIA API with pagination support
3. Transforms data to canonical schema
4. Writes to data/fuelmix.parquet
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import requests

# Constants
API_BASE_URL = "https://api.eia.gov/v2"
ENDPOINT = "electricity/rto/fuel-type-data"
RESPONDENT = "ERCO"  # ERCOT
FREQUENCY = "hourly"
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
        print("⚠️  EIA_API_KEY not found. Using demo data for development.")
        print("   To use real EIA data, set EIA_API_KEY environment variable.")
        print("   Get your free key at: https://www.eia.gov/opendata/register.php")
        return None  # Return None to trigger demo mode
    
    return api_key


def fetch_eia_data(api_key: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    Fetch fuel type data from EIA API with pagination.
    
    The EIA API returns data in pages (default 5000 rows per page).
    This function handles pagination to retrieve all available data.
    
    Args:
        api_key: EIA API key
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        
    Returns:
        DataFrame with raw API response data
    """
    all_data = []
    offset = 0
    length = 5000  # Max rows per request
    
    print(f"Fetching EIA fuel mix data from {start_date} to {end_date}...")
    
    while True:
        # Build API request
        # facets: filter criteria (respondent=ERCO for ERCOT)
        # frequency: hourly data
        # data: value is the generation in MWh
        # start/end: date range filter
        # sort: order by period (timestamp) ascending
        url = f"{API_BASE_URL}/{ENDPOINT}/data/"
        params = {
            'api_key': api_key,
            'frequency': FREQUENCY,
            'data[0]': 'value',
            'facets[respondent][]': RESPONDENT,
            'start': start_date,
            'end': end_date,
            'sort[0][column]': 'period',
            'sort[0][direction]': 'asc',
            'offset': offset,
            'length': length,
        }
        
        print(f"  Fetching offset {offset}...")
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        result = response.json()
        
        # Extract data from response
        if 'response' in result and 'data' in result['response']:
            data = result['response']['data']
            if not data:
                break  # No more data
            
            all_data.extend(data)
            
            # Check if there's more data
            total = int(result['response'].get('total', 0))  # Convert string to int
            if offset + length >= total:
                break
            
            offset += length
        else:
            break
    
    print(f"  Retrieved {len(all_data)} records")
    
    if not all_data:
        raise ValueError("No data returned from EIA API")
    
    return pd.DataFrame(all_data)


def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transform raw EIA data to canonical schema.
    
    Canonical schema:
    - period: UTC datetime
    - fuel: fuel type string
    - value_mwh: generation in MWh
    - last_updated: ISO timestamp string
    
    Args:
        df: Raw dataframe from EIA API
        
    Returns:
        Transformed dataframe with canonical schema
    """
    # Select and rename columns
    # EIA API returns: period, type-name (fuel type), value
    df_clean = df[['period', 'type-name', 'value']].copy()
    df_clean.columns = ['period', 'fuel', 'value_mwh']
    
    # Convert period to UTC datetime
    df_clean['period'] = pd.to_datetime(df_clean['period'], utc=True)
    
    # Ensure value_mwh is numeric
    df_clean['value_mwh'] = pd.to_numeric(df_clean['value_mwh'], errors='coerce')
    
    # Drop any rows with null values
    df_clean = df_clean.dropna()
    
    # Standardize fuel names (uppercase for consistency)
    df_clean['fuel'] = df_clean['fuel'].str.upper()
    
    # Add last_updated timestamp
    df_clean['last_updated'] = datetime.utcnow().isoformat()
    
    # Sort by period and fuel
    df_clean = df_clean.sort_values(['period', 'fuel']).reset_index(drop=True)
    
    return df_clean


def main():
    """Main ETL execution."""
    try:
        # Get API key
        api_key = get_api_key()
        
        # If no API key, use demo data
        if api_key is None:
            print("🔄 Generating demo fuel mix data...")
            from demo_fuelmix_data import main as generate_demo
            generate_demo()
            print("✅ Demo fuel mix data generated successfully")
            return True
        
        # Calculate date range (last 7 days)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)
        
        # Format dates for API (YYYY-MM-DD)
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        # Fetch data from EIA API
        df_raw = fetch_eia_data(api_key, start_str, end_str)
        
        # Transform to canonical schema
        df_clean = transform_data(df_raw)
        
        # Ensure data directory exists
        DATA_DIR.mkdir(exist_ok=True, parents=True)
        
        # Write to parquet with snappy compression
        output_path = DATA_DIR / "fuelmix.parquet"
        df_clean.to_parquet(
            output_path,
            engine='pyarrow',
            compression='snappy',
            index=False
        )
        
        print(f"✓ Successfully wrote {len(df_clean)} records to {output_path}")
        print(f"  Date range: {df_clean['period'].min()} to {df_clean['period'].max()}")
        print(f"  Fuel types: {', '.join(sorted(df_clean['fuel'].unique()))}")
        
    except Exception as e:
        print(f"✗ Error in ETL process: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
