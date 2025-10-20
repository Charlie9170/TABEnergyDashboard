"""
Demo Fuel Mix Data Generator

Creates realistic demo fuel mix data for development and testing.
Generates 7 days of hourly data with realistic ERCOT fuel patterns.
"""

from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import numpy as np

# Constants
DATA_DIR = Path(__file__).parent.parent / "data"


def create_demo_fuelmix() -> pd.DataFrame:
    """
    Create realistic demo fuel mix data for ERCOT.
    
    Simulates typical ERCOT generation patterns:
    - Gas: 40-60% (peaks during high demand)
    - Wind: 15-35% (higher at night, variable)
    - Solar: 0-25% (daylight hours only)
    - Coal: 5-15% (baseload)
    - Nuclear: 8-12% (steady baseload)
    
    Returns:
        DataFrame with demo fuel mix data
    """
    # Generate last 7 days of hourly data
    end_time = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    start_time = end_time - timedelta(days=7)
    
    # Create hourly timestamps
    periods = pd.date_range(start=start_time, end=end_time, freq='H', tz='UTC')
    
    all_data = []
    
    for period in periods:
        # Hour of day (0-23) for daily patterns
        hour = period.hour
        
        # Simulate demand pattern (lower at night, higher in afternoon)
        demand_factor = 0.7 + 0.3 * np.sin((hour - 6) * np.pi / 12)
        demand_factor = max(0.5, min(1.2, demand_factor))
        
        # Base load (MW) - varies by hour
        base_load = 35000 * demand_factor
        
        # Solar generation (0 at night, peak around noon)
        solar_hours = max(0, min(12, hour - 6))  # 6 AM to 6 PM
        solar_factor = np.sin(solar_hours * np.pi / 12) if solar_hours > 0 else 0
        solar_mw = base_load * 0.15 * solar_factor * np.random.uniform(0.8, 1.2)
        
        # Wind generation (higher at night, more variable)
        wind_base = 0.25 if 22 <= hour or hour <= 6 else 0.18  # Higher at night
        wind_mw = base_load * wind_base * np.random.uniform(0.6, 1.4)
        
        # Nuclear (steady baseload with small variation)
        nuclear_mw = base_load * 0.10 * np.random.uniform(0.95, 1.05)
        
        # Coal (declining baseload)
        coal_mw = base_load * 0.08 * np.random.uniform(0.8, 1.2)
        
        # Gas (fills remaining demand)
        other_renewables = base_load * 0.02 * np.random.uniform(0.5, 1.5)  # Hydro, biomass
        gas_mw = max(0, base_load - solar_mw - wind_mw - nuclear_mw - coal_mw - other_renewables)
        
        # Add small storage (can be negative for charging)
        storage_mw = base_load * 0.01 * np.random.uniform(-0.5, 1.0)
        
        # Create records for each fuel type
        fuel_data = [
            {"period": period, "fuel": "GAS", "value_mwh": gas_mw},
            {"period": period, "fuel": "WIND", "value_mwh": wind_mw},
            {"period": period, "fuel": "SUN", "value_mwh": solar_mw},
            {"period": period, "fuel": "NUCLEAR", "value_mwh": nuclear_mw},
            {"period": period, "fuel": "COAL", "value_mwh": coal_mw},
            {"period": period, "fuel": "HYDRO", "value_mwh": other_renewables * 0.6},
            {"period": period, "fuel": "BIOMASS", "value_mwh": other_renewables * 0.4},
            {"period": period, "fuel": "STORAGE", "value_mwh": storage_mw},
        ]
        
        all_data.extend(fuel_data)
    
    # Create DataFrame
    df = pd.DataFrame(all_data)
    
    # Add last_updated timestamp
    df['last_updated'] = datetime.utcnow().isoformat()
    
    return df


def main():
    """Generate demo fuel mix data."""
    print("Creating demo fuel mix data...")
    
    # Ensure data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Generate data
    df = create_demo_fuelmix()
    
    # Write to parquet
    output_path = DATA_DIR / "fuelmix.parquet"
    df.to_parquet(output_path, engine='pyarrow', compression='snappy', index=False)
    
    print(f"✓ Successfully wrote {len(df)} records to {output_path}")
    print(f"  Time range: {df['period'].min()} to {df['period'].max()}")
    print(f"  Fuels: {', '.join(sorted(df['fuel'].unique()))}")
    print(f"  Total generation range: {df.groupby('period')['value_mwh'].sum().min():.0f} - {df.groupby('period')['value_mwh'].sum().max():.0f} MW")
    
    print("\nNOTE: This is demo data for development.")
    print("Replace with real EIA API data by setting EIA_API_KEY and running eia_fuelmix_etl.py")


if __name__ == "__main__":
    main()