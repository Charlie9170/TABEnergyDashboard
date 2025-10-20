"""Create demo fuel mix data for testing the dashboard."""

import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.utils.data_loader import save_fuel_mix_data

def create_demo_data():
    """Create demo fuel mix data."""
    # Create 7 days of hourly data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    # Generate hourly timestamps
    periods = pd.date_range(start=start_date, end=end_date, freq='H')
    
    # Fuel types
    fuel_types = ['coal', 'natural gas', 'nuclear', 'wind', 'solar', 'hydro']
    
    # Create base patterns for each fuel type
    data_list = []
    
    for period in periods:
        hour = period.hour
        
        # Base generation patterns (realistic for ERCOT)
        patterns = {
            'coal': 3000 + np.random.normal(0, 200),  # Steady baseload
            'natural gas': 15000 + np.random.normal(0, 2000) + (1000 if 10 <= hour <= 20 else -500),  # Peaking
            'nuclear': 5000 + np.random.normal(0, 100),  # Very steady baseload
            'wind': 8000 + np.random.normal(0, 2000) + (2000 if hour in [0, 1, 2, 3, 22, 23] else 0),  # Night peak
            'solar': max(0, 3000 * np.sin((hour - 6) * np.pi / 12)) if 6 <= hour <= 18 else 0,  # Daytime only
            'hydro': 500 + np.random.normal(0, 50),  # Small steady
        }
        
        for fuel, value in patterns.items():
            data_list.append({
                'period': period,
                'fuel': fuel,
                'value_mwh': max(0, value),  # Ensure non-negative
                'last_updated': datetime.now()
            })
    
    # Create DataFrame
    df = pd.DataFrame(data_list)
    
    print(f"Created {len(df)} demo records")
    print(f"Date range: {df['period'].min()} to {df['period'].max()}")
    print(f"Fuel types: {df['fuel'].unique()}")
    
    # Save to parquet
    save_fuel_mix_data(df)
    print("Demo data saved successfully!")

if __name__ == '__main__':
    create_demo_data()
