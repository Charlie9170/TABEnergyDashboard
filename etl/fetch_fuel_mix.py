"""ETL script to fetch ERCOT fuel mix data from EIA API v2."""

import os
import sys
import requests
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.data_loader import save_fuel_mix_data, get_fuel_mix_schema

# EIA API v2 endpoint for ERCOT hourly data
EIA_API_BASE = "https://api.eia.gov/v2/electricity/rto/fuel-type-data/data/"

def fetch_eia_fuel_mix(api_key, start_date=None, end_date=None, limit=5000):
    """Fetch fuel mix data from EIA API v2.
    
    Args:
        api_key: EIA API key
        start_date: Start date for data fetch (YYYY-MM-DD)
        end_date: End date for data fetch (YYYY-MM-DD)
        limit: Maximum number of records to fetch
        
    Returns:
        DataFrame with fuel mix data
    """
    # Default to last 7 days if no dates provided
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    params = {
        'api_key': api_key,
        'frequency': 'hourly',
        'data[0]': 'value',
        'facets[respondent][]': 'ERCO',  # ERCOT region
        'start': start_date,
        'end': end_date,
        'sort[0][column]': 'period',
        'sort[0][direction]': 'desc',
        'offset': 0,
        'length': limit
    }
    
    try:
        response = requests.get(EIA_API_BASE, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if 'response' not in data or 'data' not in data['response']:
            raise ValueError("Unexpected API response format")
        
        records = data['response']['data']
        
        if not records:
            print(f"No data returned for date range {start_date} to {end_date}")
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(records)
        
        # Transform to match schema
        transformed_df = pd.DataFrame({
            'period': pd.to_datetime(df['period']),
            'fuel': df['fueltype'].str.lower(),
            'value_mwh': pd.to_numeric(df['value'], errors='coerce'),
            'last_updated': datetime.now()
        })
        
        # Remove any null values
        transformed_df = transformed_df.dropna()
        
        print(f"Fetched {len(transformed_df)} records from EIA API")
        return transformed_df
        
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Error fetching data from EIA API: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Error processing EIA data: {str(e)}")

def main():
    """Main ETL execution."""
    print("=" * 60)
    print("TAB Energy Dashboard - Fuel Mix ETL")
    print("=" * 60)
    
    # Get API key from environment
    api_key = os.getenv('EIA_API_KEY')
    if not api_key:
        print("ERROR: EIA_API_KEY environment variable not set")
        print("Please set your EIA API key:")
        print("  export EIA_API_KEY='your_api_key_here'")
        print("\nGet a free API key at: https://www.eia.gov/opendata/register.php")
        return 1
    
    try:
        # Fetch data from EIA
        print("\nFetching fuel mix data from EIA API...")
        df = fetch_eia_fuel_mix(api_key)
        
        if df.empty:
            print("No data fetched. Check API parameters and try again.")
            return 1
        
        # Display summary
        print(f"\nData Summary:")
        print(f"  Records: {len(df)}")
        print(f"  Date Range: {df['period'].min()} to {df['period'].max()}")
        print(f"  Fuel Types: {', '.join(df['fuel'].unique())}")
        
        # Save to parquet
        print("\nSaving data to parquet...")
        save_fuel_mix_data(df)
        
        data_path = Path(__file__).parent.parent / 'data' / 'ercot_fuel_mix.parquet'
        print(f"Data saved to: {data_path}")
        
        print("\n" + "=" * 60)
        print("ETL completed successfully!")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
