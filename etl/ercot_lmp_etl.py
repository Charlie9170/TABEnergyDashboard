"""
ERCOT Real-Time LMP ETL Script

Fetches real-time Locational Marginal Prices (LMP) from ERCOT Public HTML page.
Extracts zone-level prices for visualization on the dashboard.

Data Source: ERCOT Real-Time Settlement Point Prices (Public, Free)
Update Frequency: Every 5 minutes (from ERCOT)
Auto-Update: Configured to run every 6 hours via GitHub Actions

Author: TAB Energy Dashboard
Date: 2025-11-10
"""

import requests
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
import logging
import sys
from typing import Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Data directory
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# ERCOT Zones with coordinates (for map visualization)
# These correspond to the columns in ERCOT's real-time SPP table
# Coordinates optimized for better visual spacing on map
# 
# TIER CLASSIFICATION:
# - 'hub': Major load zones (8 zones) - DEFAULT view, fast rendering, proven stable
# - 'strategic': Detailed strategic nodes (2 nodes) - OPTIONAL view for granularity
#
# NOTE: Only settlement points that ERCOT actually publishes data for are included.
# ERCOT provides real-time LMP data for 10 total nodes (8 hubs + 2 strategic).
ERCOT_ZONES = {
    # ===== MAJOR HUBS (8 zones - TIER: hub) =====
    'HB_NORTH': {'name': 'North (Dallas)', 'lat': 33.0, 'lon': -96.5, 'tier': 'hub'},
    'HB_HOUSTON': {'name': 'Houston', 'lat': 29.5, 'lon': -95.0, 'tier': 'hub'},
    'HB_SOUTH': {'name': 'South (Corpus/Laredo)', 'lat': 27.5, 'lon': -98.5, 'tier': 'hub'},
    'HB_WEST': {'name': 'West (Odessa/Midland)', 'lat': 31.8, 'lon': -102.5, 'tier': 'hub'},
    'LZ_SOUTH': {'name': 'South Central (Austin)', 'lat': 30.0, 'lon': -97.5, 'tier': 'hub'},
    'LZ_NORTH': {'name': 'East (Tyler/Longview)', 'lat': 32.5, 'lon': -94.5, 'tier': 'hub'},
    'HB_PAN': {'name': 'Panhandle (Amarillo)', 'lat': 35.5, 'lon': -101.5, 'tier': 'hub'},
    'HB_BUSAVG': {'name': 'Grid Average', 'lat': 31.0, 'lon': -100.0, 'tier': 'hub'},
    
    # ===== STRATEGIC NODES (2 additional locations - TIER: strategic) =====
    # These provide granular detail within major hub regions
    'LZ_HOUSTON': {'name': 'Houston Central', 'lat': 29.76, 'lon': -95.37, 'tier': 'strategic'},
    'LZ_WEST': {'name': 'Midland', 'lat': 31.99, 'lon': -102.08, 'tier': 'strategic'},
}


def fetch_ercot_realtime_spp() -> Optional[pd.DataFrame]:
    """
    Fetch latest Settlement Point Prices from ERCOT public HTML page.
    
    Returns:
        DataFrame with columns: zone, zone_key, avg_price, lat, lon, interval_end, timestamp, last_updated
        Returns None if data cannot be fetched
    """
    try:
        logger.info("Fetching real-time settlement point prices from ERCOT...")
        
        # ERCOT Real-Time SPP endpoint (HTML table, updated every 5 minutes)
        url = "https://www.ercot.com/content/cdr/html/real_time_spp"
        
        headers = {
            'User-Agent': 'TAB-Energy-Dashboard/1.0'
        }
        
        response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
        response.raise_for_status()
        
        logger.info(f"Successfully fetched data ({len(response.content)} bytes)")
        
        # Parse HTML table (BeautifulSoup accepts bytes directly)
        soup = BeautifulSoup(response.content, 'html.parser')  # type: ignore
        table = soup.find('table', class_='tableStyle')
        
        if not table:
            logger.error("Could not find price table in HTML")
            return None
        
        # Extract headers
        headers_row = table.find('tr')
        headers = [th.text.strip() for th in headers_row.find_all('th')]
        logger.info(f"Found {len(headers)} columns")
        
        # Extract data rows
        data_rows = []
        for row in table.find_all('tr')[1:]:  # Skip header row
            cols = row.find_all('td')
            if len(cols) > 0:
                row_data = [col.text.strip() for col in cols]
                if len(row_data) == len(headers):
                    data_rows.append(row_data)
        
        if not data_rows:
            logger.error("No data rows found in table")
            return None
        
        logger.info(f"Extracted {len(data_rows)} interval rows")
        
        # Create DataFrame
        df = pd.DataFrame(data_rows, columns=headers)
        
        # Get the most recent interval (last row has latest data)
        latest_row = df.iloc[-1]
        interval_end = latest_row['Interval Ending']
        oper_day = latest_row['Oper Day']
        
        # Transform to long format (one row per zone)
        zone_data = []
        for col in headers[2:]:  # Skip 'Oper Day' and 'Interval Ending'
            if col in ERCOT_ZONES:
                try:
                    # Get scalar value from Series to avoid type checker warnings
                    price_value = latest_row[col]
                    price_mwh = float(price_value)  # type: ignore - LMP in $/MWh
                    
                    # Convert $/MWh to cents/kWh: divide by 10
                    # (1 MWh = 1000 kWh, so $X/MWh = X/10 cents/kWh)
                    price_cperkwh = price_mwh / 10.0
                    
                    zone_data.append({
                        'node_id': col,  # Zone key (matches schema)
                        'region': ERCOT_ZONES[col]['name'],  # Zone name (matches schema)
                        'price_cperkwh': price_cperkwh,  # Price in cents/kWh (matches schema)
                        'lat': ERCOT_ZONES[col]['lat'],
                        'lon': ERCOT_ZONES[col]['lon'],
                        'tier': ERCOT_ZONES[col]['tier'],  # Hub vs strategic classification
                        'last_updated': datetime.now().isoformat(),  # ISO format timestamp
                        # Keep raw data for reference
                        'zone_key': col,
                        'avg_price': price_mwh,  # Original $/MWh for debugging
                        'interval_end': interval_end,
                        'oper_day': oper_day,
                    })
                except (ValueError, KeyError) as e:
                    logger.warning(f"Skipping column {col}: {str(e)}")
                    continue
        
        result_df = pd.DataFrame(zone_data)
        logger.info(f"Processed {len(result_df)} zones with price data")
        
        # Log tier breakdown
        if 'tier' in result_df.columns:
            hub_count = len(result_df[result_df['tier'] == 'hub'])
            strategic_count = len(result_df[result_df['tier'] == 'strategic'])
            logger.info(f"  → {hub_count} major hubs (tier='hub')")
            logger.info(f"  → {strategic_count} strategic nodes (tier='strategic')")
        
        # Log sample prices in both formats
        if len(result_df) > 0:
            avg_price_mwh = result_df['avg_price'].mean()
            min_price_mwh = result_df['avg_price'].min()
            max_price_mwh = result_df['avg_price'].max()
            logger.info(f"Price range: ${min_price_mwh:.2f} - ${max_price_mwh:.2f}/MWh (avg: ${avg_price_mwh:.2f})")
            
            avg_price_cperkwh = result_df['price_cperkwh'].mean()
            min_price_cperkwh = result_df['price_cperkwh'].min()
            max_price_cperkwh = result_df['price_cperkwh'].max()
            logger.info(f"             {min_price_cperkwh:.2f} - {max_price_cperkwh:.2f} ¢/kWh (avg: {avg_price_cperkwh:.2f})")
        
        return result_df
        
    except requests.exceptions.RequestException as e:
        logger.error(f"HTTP request failed: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Failed to parse HTML: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def save_to_parquet(df: pd.DataFrame) -> bool:
    """
    Save DataFrame to parquet file (atomic write).
    
    Args:
        df: DataFrame with price data
        
    Returns:
        True if successful, False otherwise
    """
    try:
        output_file = DATA_DIR / "price_map.parquet"
        temp_file = DATA_DIR / "price_map.parquet.tmp"
        
        # Write to temp file first
        df.to_parquet(temp_file, index=False, engine='pyarrow')
        
        # Verify file was written
        test_df = pd.read_parquet(temp_file)
        if len(test_df) != len(df):
            logger.error("Verification failed: row count mismatch")
            temp_file.unlink(missing_ok=True)
            return False
        
        # Atomic move
        temp_file.replace(output_file)
        
        logger.info(f"✅ Saved {len(df)} records to {output_file}")
        logger.info(f"   File size: {output_file.stat().st_size:,} bytes")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to save parquet: {str(e)}")
        return False


def main():
    """Main ETL execution."""
    logger.info("=" * 60)
    logger.info("ERCOT Real-Time LMP ETL - Starting")
    logger.info("=" * 60)
    
    # Fetch data
    df = fetch_ercot_realtime_spp()
    
    if df is None or len(df) == 0:
        logger.error("❌ Failed to fetch ERCOT data")
        sys.exit(1)
    
    # Save to parquet
    if not save_to_parquet(df):
        logger.error("❌ Failed to save data")
        sys.exit(1)
    
    logger.info("=" * 60)
    logger.info("✅ ERCOT Real-Time LMP ETL - Completed Successfully")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
