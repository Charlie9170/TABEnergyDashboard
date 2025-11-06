#!/usr/bin/env python3
"""
ERCOT Interconnection Queue ETL Script

This script downloads and processes ERCOT Capacity, Demand and Reserves (CDR) report
to extract interconnection queue data for the Texas Association of Business Energy Dashboard.

Features:
- Parses ERCOT CDR Excel report for planned and future generation projects
- Extracts project timeline, capacity, fuel type, and status information  
- Generates realistic Texas coordinates for geographic visualization
- Implements robust error handling, logging, and data validation
- Outputs clean parquet file for dashboard consumption

Data Source: ERCOT CDR Report (https://www.ercot.com/gridinfo/resource)
Output: data/queue.parquet

Usage:
    python etl/ercot_queue_etl.py

Author: Texas Association of Business Energy Dashboard
Created: October 2025
"""

import logging
import os
import sys
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import hashlib
import tempfile
import shutil

import pandas as pd
import numpy as np
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Ensure we can import from the same directory (for GitHub Actions)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import Texas county geocoding
try:
    from texas_counties import get_county_coordinates, validate_coordinates
except ImportError as e:
    # If import fails, log detailed error
    import traceback
    print(f"ERROR: Failed to import texas_counties module: {e}")
    print(f"Current directory: {os.getcwd()}")
    print(f"Script directory: {os.path.dirname(os.path.abspath(__file__))}")
    print(f"Python path: {sys.path}")
    traceback.print_exc()
    raise ImportError("texas_counties.py must be in the etl/ directory") from e


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Also log to file
file_handler = logging.FileHandler('etl_queue.log')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


class ETLValidationError(Exception):
    """Custom exception for ETL validation errors"""
    pass


class ETLProcessingError(Exception):  
    """Custom exception for ETL processing errors"""
    pass


def validate_queue_schema(df: pd.DataFrame) -> bool:
    """
    Validate that the queue DataFrame has the expected structure.
    
    Args:
        df: DataFrame to validate
        
    Returns:
        bool: True if valid, raises ETLValidationError if invalid
        
    Raises:
        ETLValidationError: If schema validation fails
    """
    required_columns = [
        'project_name', 'capacity_mw', 'fuel_type', 'status', 
        'expected_date', 'county', 'technology', 'lat', 'lon'
    ]
    
    missing_columns = set(required_columns) - set(df.columns)
    if missing_columns:
        raise ETLValidationError(f"Missing required columns: {missing_columns}")
    
    # Validate data types and ranges
    if not pd.api.types.is_numeric_dtype(df['capacity_mw']):
        raise ETLValidationError("capacity_mw must be numeric")
    
    if df['capacity_mw'].min() < 0:
        raise ETLValidationError("capacity_mw cannot be negative")
    
    if not pd.api.types.is_numeric_dtype(df['lat']) or not pd.api.types.is_numeric_dtype(df['lon']):
        raise ETLValidationError("lat and lon must be numeric")
    
    # Check Texas coordinate bounds
    texas_lat_bounds = (25.84, 36.50)
    texas_lon_bounds = (-106.65, -93.51)
    
    invalid_coords = (
        (df['lat'] < texas_lat_bounds[0]) | (df['lat'] > texas_lat_bounds[1]) |
        (df['lon'] < texas_lon_bounds[0]) | (df['lon'] > texas_lon_bounds[1])
    )
    
    if invalid_coords.sum() > 0:
        logger.warning(f"Found {invalid_coords.sum()} projects outside Texas bounds")
    
    logger.info(f"✅ Schema validation passed for {len(df)} projects")
    return True


def get_county_coordinates_for_project(
    project_name: str, 
    county: str, 
    fuel_type: str
) -> Tuple[float, float]:
    """
    Get real coordinates for project based on its Texas county.
    
    Uses static county centroid database (texas_counties.py) for reliable,
    offline geocoding. Adds small random jitter to prevent overlapping dots
    for multiple projects in the same county.
    
    Args:
        project_name: Name of the energy project (for jitter seed)
        county: County location from ERCOT data (e.g., "HARRIS")
        fuel_type: Fuel type (for logging context only)
        
    Returns:
        Tuple of (latitude, longitude) with county centroid + jitter
        
    Example:
        >>> get_county_coordinates_for_project("Solar Farm 1", "HARRIS", "Solar")
        (29.7821, -95.3512)  # Harris County centroid + small jitter
    """
    # Get real county centroid from static database
    lat, lon = get_county_coordinates(county)
    
    # Add tiny random jitter (±0.03 degrees ≈ 2 miles) to avoid overlapping dots
    # Uses project name as seed for deterministic results
    project_hash = hashlib.md5(f"{project_name}{county}".encode()).hexdigest()
    base_seed = int(project_hash[:8], 16)
    np.random.seed(base_seed % (2**32))
    
    jitter_lat = np.random.uniform(-0.03, 0.03)
    jitter_lon = np.random.uniform(-0.03, 0.03)
    
    final_lat = round(lat + jitter_lat, 4)
    final_lon = round(lon + jitter_lon, 4)
    
    # Validate final coordinates are still in Texas
    if not validate_coordinates(final_lat, final_lon):
        logger.warning(
            f"Jittered coordinates for {project_name} in {county} "
            f"fell outside Texas bounds. Using exact centroid."
        )
        return round(lat, 4), round(lon, 4)
    
    return final_lat, final_lon


def parse_ercot_cdr_data(file_path: str) -> pd.DataFrame:
    """
    Parse ERCOT CDR Excel file to extract interconnection queue data.
    
    Args:
        file_path: Path to ERCOT CDR Excel file
        
    Returns:
        DataFrame with standardized queue project data
        
    Raises:
        ETLProcessingError: If parsing fails
    """
    logger.info(f"Parsing ERCOT CDR data from {file_path}")
    
    try:
        # Read Unit Details sheet with proper header parsing
        df_raw = pd.read_excel(file_path, sheet_name='Unit Details', skiprows=7)
        
        # Find the header row containing "UNIT NAME"
        header_idx: Optional[int] = None
        for idx, row in df_raw.iterrows():
            # Convert pandas index to integer for comparison
            i = int(idx) if isinstance(idx, (int, float)) else 0
            if i > 10:  # Don't search too far
                break
            row_str = str(row.iloc[0]) if not pd.isna(row.iloc[0]) else ""
            if 'UNIT NAME' in row_str:
                header_idx = i
                break
        
        if header_idx is None:
            raise ETLProcessingError("Could not find header row with UNIT NAME")
        
        # Extract data starting from header
        header_row = df_raw.iloc[header_idx]
        unit_data = df_raw.iloc[header_idx + 1:].copy()
        
        # Clean up column names
        new_columns = []
        for j, col_name in enumerate(header_row):
            if pd.isna(col_name) or str(col_name).startswith('Unnamed'):
                new_columns.append(f'col_{j}')
            else:
                # Clean up column names (remove newlines, extra spaces)
                clean_name = str(col_name).strip().replace('\n', '_').replace('  ', ' ')
                new_columns.append(clean_name)
        
        unit_data.columns = new_columns
        unit_data = unit_data.dropna(how='all').reset_index(drop=True)
        
        logger.info(f"Parsed {len(unit_data)} total units from CDR report")
        
        # Filter for planned projects (queue data)
        if 'CDR STATUS' not in unit_data.columns:
            raise ETLProcessingError("CDR STATUS column not found in parsed data")
        
        queue_projects = unit_data[
            unit_data['CDR STATUS'].isin(['PLAN', 'PLAN-SLF'])
        ].copy()
        
        logger.info(f"Found {len(queue_projects)} planned projects in interconnection queue")
        
        if queue_projects.empty:
            raise ETLProcessingError("No planned projects found in CDR data")
        
        # Standardize the DataFrame structure
        standardized_df = pd.DataFrame()
        
        # Map columns to standard names
        standardized_df['project_name'] = queue_projects['UNIT NAME'].fillna('Unknown Project')
        standardized_df['fuel_type'] = queue_projects['FUEL'].fillna('Unknown')
        standardized_df['technology'] = queue_projects['TECHNOLOGY'].fillna('Unknown')
        standardized_df['status'] = queue_projects['CDR STATUS'].fillna('PLAN')
        standardized_df['county'] = queue_projects['COUNTY'].fillna('Unknown County')
        
        # Extract capacity from installed capacity column
        capacity_col = None
        for col in queue_projects.columns:
            if 'INSTALLED CAPACITY' in col and 'MW' in col:
                capacity_col = col
                break
        
        if capacity_col:
            standardized_df['capacity_mw'] = pd.to_numeric(
                queue_projects[capacity_col], errors='coerce'
            ).fillna(0)
        else:
            # Fallback to reasonable default for planned projects
            logger.warning("Could not find capacity column, using default values")
            standardized_df['capacity_mw'] = 100.0  # Default 100 MW
        
        # Extract in-service date
        date_col = None
        for col in queue_projects.columns:
            if 'IN-SERVICE' in col and 'DATE' in col:
                date_col = col
                break
        
        if date_col:
            standardized_df['expected_date'] = pd.to_datetime(
                queue_projects[date_col], errors='coerce'
            )
        else:
            # Default to future dates for planned projects
            logger.warning("Could not find in-service date column, using default dates")
            base_date = pd.Timestamp('2026-01-01')
            standardized_df['expected_date'] = [
                base_date + pd.Timedelta(days=i*30) for i in range(len(standardized_df))
            ]
        
        # Add accurate coordinates based on county centroids
        coordinates = []
        for _, row in standardized_df.iterrows():
            lat, lon = get_county_coordinates_for_project(
                row['project_name'], row['county'], row['fuel_type']
            )
            coordinates.append((lat, lon))
        
        standardized_df['lat'] = [coord[0] for coord in coordinates]
        standardized_df['lon'] = [coord[1] for coord in coordinates]
        
        # Convert dates to strings for JSON serialization
        standardized_df['expected_date'] = standardized_df['expected_date'].dt.strftime('%Y-%m-%d')
        
        # Add metadata
        standardized_df['data_source'] = 'ERCOT CDR Report'
        standardized_df['last_updated'] = datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')
        
        # Clean up fuel types for consistency
        fuel_mapping = {
            'GAS': 'Natural Gas',
            'WIND-O': 'Wind',
            'SOLAR-O': 'Solar',
            'SOLAR-W': 'Solar', 
            'STORAGE': 'Battery Storage',
            'NATGAS': 'Natural Gas'
        }
        standardized_df['fuel_type'] = standardized_df['fuel_type'].map(fuel_mapping).fillna(standardized_df['fuel_type'])
        
        logger.info(f"✅ Successfully standardized {len(standardized_df)} queue projects")
        
        # Log summary statistics
        logger.info("Queue Summary:")
        logger.info(f"  Total capacity: {standardized_df['capacity_mw'].sum():,.0f} MW")
        logger.info(f"  Fuel mix: {standardized_df['fuel_type'].value_counts().to_dict()}")
        logger.info(f"  Status distribution: {standardized_df['status'].value_counts().to_dict()}")
        
        return standardized_df
        
    except Exception as e:
        logger.error(f"Failed to parse ERCOT CDR data: {e}")
        raise ETLProcessingError(f"CDR parsing failed: {e}")


def atomic_write_parquet(df: pd.DataFrame, output_path: str) -> None:
    """
    Write DataFrame to parquet file atomically using temporary file.
    
    Args:
        df: DataFrame to write
        output_path: Final output file path
        
    Raises:
        ETLProcessingError: If write operation fails
    """
    logger.info(f"Writing {len(df)} records to {output_path}")
    
    try:
        # Write to temporary file first
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        with tempfile.NamedTemporaryFile(
            mode='wb', 
            suffix='.parquet',
            dir=output_dir,
            delete=False
        ) as tmp_file:
            temp_path = tmp_file.name
        
        # Write DataFrame to temporary file
        df.to_parquet(temp_path, index=False, engine='pyarrow')
        
        # Verify the file was written correctly
        test_df = pd.read_parquet(temp_path)
        if len(test_df) != len(df):
            raise ETLProcessingError(f"Verification failed: expected {len(df)} rows, got {len(test_df)}")
        
        # Atomically move to final location
        shutil.move(temp_path, output_path)
        logger.info(f"✅ Successfully wrote queue data to {output_path}")
        
    except Exception as e:
        # Clean up temporary file if it exists
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.unlink(temp_path)
        logger.error(f"Failed to write parquet file: {e}")
        raise ETLProcessingError(f"File write failed: {e}")


def download_cdr_report(output_path: str) -> bool:
    """
    Download latest ERCOT CDR report if not already present.
    
    Args:
        output_path: Where to save the downloaded file
        
    Returns:
        bool: True if download successful or file already exists
    """
    if os.path.exists(output_path):
        logger.info(f"CDR report already exists at {output_path}")
        return True
    
    cdr_url = "https://www.ercot.com/files/docs/2025/05/16/CapacityDemandandReservesReport_May2025_Revised.xlsx"
    
    logger.info(f"Downloading ERCOT CDR report from {cdr_url}")
    
    try:
        # Create HTTP session with retry strategy
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        response = session.get(cdr_url, timeout=60)
        response.raise_for_status()
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'wb') as f:
            f.write(response.content)
        
        logger.info(f"✅ Successfully downloaded CDR report ({len(response.content):,} bytes)")
        return True
        
    except Exception as e:
        logger.error(f"Failed to download CDR report: {e}")
        return False


def main():
    """Main ETL execution function"""
    logger.info("=" * 60)
    logger.info("🚀 STARTING ERCOT INTERCONNECTION QUEUE ETL")
    logger.info("=" * 60)
    
    try:
        # File paths
        cdr_file_path = "data/ercot_cdr_may2025.xlsx"
        output_file_path = "data/queue.parquet"
        
        # Download CDR report if needed
        if not download_cdr_report(cdr_file_path):
            raise ETLProcessingError("Could not download or access CDR report")
        
        # Parse CDR data to extract queue information
        logger.info("🔄 Parsing ERCOT CDR data...")
        queue_df = parse_ercot_cdr_data(cdr_file_path)
        
        # Validate data schema
        logger.info("✅ Validating data schema...")
        validate_queue_schema(queue_df)
        
        # Write to output file
        logger.info("💾 Writing queue data...")
        atomic_write_parquet(queue_df, output_file_path)
        
        # Final summary
        logger.info("=" * 60)
        logger.info("🎉 ERCOT QUEUE ETL COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)
        logger.info(f"📊 Projects in queue: {len(queue_df)}")
        logger.info(f"⚡ Total planned capacity: {queue_df['capacity_mw'].sum():,.0f} MW")
        logger.info(f"📁 Output file: {output_file_path}")
        logger.info(f"🕒 Last updated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        return True
        
    except (ETLValidationError, ETLProcessingError) as e:
        logger.error(f"❌ ETL process failed: {e}")
        return False
    except Exception as e:
        logger.error(f"💥 Unexpected error in ETL process: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)