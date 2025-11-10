#!/usr/bin/env python3
"""
Texas REE & Critical Minerals ETL Script

This script processes mineral deposit data for the Texas Association of Business
Energy Dashboard, focusing on Rare Earth Elements (REEs) and Critical Minerals.

Features:
- Loads mineral deposit data from manual CSV or GeoJSON sources
- Filters deposits to Texas geographic boundaries
- Classifies deposits by development status (Major, Early, Exploratory, Discovery)
- Validates coordinates and data quality
- Outputs clean parquet file for dashboard visualization

Data Categories:
- Major Development: Round Top Mountain, Smackover Formation (Lithium)
- Early Development: Zinc, Helium extraction facilities
- Exploratory: Brewster County REEs, Cave Peak, Dell City surveys
- Discovery: Initial prospecting sites

Usage:
    python etl/mineral_etl.py

Author: Texas Association of Business Energy Dashboard
Created: November 2025
"""

import logging
import os
import sys
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import tempfile
import shutil

import pandas as pd
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Also log to file
file_handler = logging.FileHandler('etl_minerals.log')
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


# Texas geographic boundaries
TEXAS_BOUNDS = {
    'lat_min': 25.84,
    'lat_max': 36.50,
    'lon_min': -106.65,
    'lon_max': -93.51
}


def validate_texas_coordinates(lat: float, lon: float) -> bool:
    """
    Validate that coordinates fall within Texas boundaries.
    
    Args:
        lat: Latitude
        lon: Longitude
        
    Returns:
        bool: True if within Texas, False otherwise
    """
    return (
        TEXAS_BOUNDS['lat_min'] <= lat <= TEXAS_BOUNDS['lat_max'] and
        TEXAS_BOUNDS['lon_min'] <= lon <= TEXAS_BOUNDS['lon_max']
    )


def load_manual_deposits(csv_path: str) -> pd.DataFrame:
    """
    Load manually curated mineral deposit data from CSV.
    
    Expected CSV columns:
    - deposit_name: Name of the mineral deposit/site
    - lat: Latitude (decimal degrees)
    - lon: Longitude (decimal degrees)
    - minerals: Comma-separated list of minerals (e.g., "Lithium, REEs")
    - estimated_tonnage: Estimated resource tonnage (numeric, or TBD)
    - development_status: Major, Early, Exploratory, Discovery
    - county: Texas county name
    - details: Additional description/notes
    
    Args:
        csv_path: Path to manual deposits CSV file
        
    Returns:
        DataFrame with mineral deposit data
        
    Raises:
        ETLProcessingError: If file cannot be loaded or parsed
    """
    logger.info(f"Loading manual deposit data from {csv_path}")
    
    if not os.path.exists(csv_path):
        logger.warning(f"Manual deposits CSV not found at {csv_path}")
        logger.info("Creating empty DataFrame with expected schema")
        return pd.DataFrame(columns=[
            'deposit_name', 'lat', 'lon', 'minerals', 'estimated_tonnage',
            'development_status', 'county', 'details'
        ])
    
    try:
        df = pd.read_csv(csv_path)
        logger.info(f"Loaded {len(df)} manual deposits from CSV")
        return df
        
    except Exception as e:
        logger.error(f"Failed to load manual deposits CSV: {e}")
        raise ETLProcessingError(f"CSV load failed: {e}")


def load_geojson_deposits(geojson_path: str) -> pd.DataFrame:
    """
    Load mineral deposit data from GeoJSON file.
    
    TODO: Implement GeoJSON loading when source data is available.
    This function should:
    1. Read GeoJSON using geopandas or json library
    2. Extract geometry coordinates (Point features)
    3. Parse properties for mineral types, tonnage estimates
    4. Convert to pandas DataFrame with standardized columns
    
    Args:
        geojson_path: Path to GeoJSON file
        
    Returns:
        DataFrame with mineral deposit data
    """
    logger.info(f"GeoJSON loading not yet implemented for {geojson_path}")
    logger.info("Using manual CSV data only")
    
    # Placeholder - return empty DataFrame for now
    return pd.DataFrame(columns=[
        'deposit_name', 'lat', 'lon', 'minerals', 'estimated_tonnage',
        'development_status', 'county', 'details'
    ])


def clean_and_validate_deposits(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and validate mineral deposit data.
    
    Operations:
    - Convert lat/lon to float, drop invalid coordinates
    - Filter to Texas geographic boundaries
    - Standardize development_status values
    - Handle missing/invalid tonnage estimates
    - Remove duplicate deposits
    
    Args:
        df: Raw deposits DataFrame
        
    Returns:
        Cleaned and validated DataFrame
        
    Raises:
        ETLValidationError: If critical validation fails
    """
    logger.info(f"Cleaning and validating {len(df)} deposit records")
    
    if df.empty:
        logger.warning("No deposit data to clean")
        return df
    
    original_count = len(df)
    
    # Convert coordinates to numeric, drop invalid
    df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
    df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
    
    # Drop rows with missing coordinates
    df = df.dropna(subset=['lat', 'lon'])
    if len(df) < original_count:
        logger.info(f"Dropped {original_count - len(df)} deposits with invalid coordinates")
    
    # Filter to Texas boundaries
    texas_mask = df.apply(
        lambda row: validate_texas_coordinates(row['lat'], row['lon']), 
        axis=1
    )
    df = df[texas_mask].copy()
    logger.info(f"Kept {len(df)} deposits within Texas boundaries")
    
    # Standardize development_status
    valid_statuses = ['Major', 'Early', 'Exploratory', 'Discovery']
    if 'development_status' in df.columns:
        df['development_status'] = df['development_status'].str.title()
        invalid_status = ~df['development_status'].isin(valid_statuses)
        if invalid_status.any():
            logger.warning(f"Found {invalid_status.sum()} deposits with invalid status")
            df.loc[invalid_status, 'development_status'] = 'Exploratory'
    else:
        logger.warning("No development_status column found, setting default")
        df['development_status'] = 'Exploratory'
    
    # Handle estimated_tonnage
    if 'estimated_tonnage' in df.columns:
        df['estimated_tonnage'] = pd.to_numeric(
            df['estimated_tonnage'].replace(['TBD', 'Unknown', ''], np.nan),
            errors='coerce'
        )
        df['estimated_tonnage'] = df['estimated_tonnage'].fillna(0)
    else:
        df['estimated_tonnage'] = 0
    
    # Ensure required columns exist
    required_cols = ['deposit_name', 'lat', 'lon', 'minerals', 'development_status']
    for col in required_cols:
        if col not in df.columns:
            raise ETLValidationError(f"Missing required column: {col}")
    
    # Fill missing optional columns
    if 'county' not in df.columns:
        df['county'] = 'Unknown'
    if 'details' not in df.columns:
        df['details'] = ''
    
    # Remove duplicate deposits (same name and location)
    df = df.drop_duplicates(subset=['deposit_name', 'lat', 'lon'])
    
    logger.info(f"✅ Cleaned data: {len(df)} valid deposits")
    
    return df


def add_visualization_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add columns needed for dashboard visualization.
    
    Adds:
    - color: Hex color code based on development_status
    - radius: Map marker size based on estimated_tonnage (refined scaling)
    - tooltip: Formatted text for hover display
    
    Args:
        df: Clean deposits DataFrame
        
    Returns:
        DataFrame with visualization columns added
    """
    logger.info("Adding visualization columns for dashboard")
    
    # Professional color palette matching TAB brand
    # Using softer, more refined colors for better visual hierarchy
    status_colors = {
        'Major': [200, 16, 46, 220],       # TAB Red (strong but not overpowering)
        'Early': [255, 140, 0, 200],        # Warm Orange
        'Exploratory': [241, 196, 15, 180], # Soft Gold (less harsh than pure yellow)
        'Discovery': [27, 54, 93, 160]      # TAB Navy (instead of gray, more cohesive)
    }
    
    df['color'] = df['development_status'].map(status_colors)
    
    # Refined radius scaling: smaller, more proportional markers
    # Range: 2,500-12,000 pixels (much smaller than before for cleaner look)
    df['radius'] = df['estimated_tonnage'].apply(
        lambda x: 2500 + (np.log10(max(x, 1)) * 3000) if x > 0 else 2500
    )
    
    # Create formatted tooltip text
    df['tooltip'] = df.apply(
        lambda row: (
            f"{row['deposit_name']}\n"
            f"Minerals: {row['minerals']}\n"
            f"Status: {row['development_status']}\n"
            f"Est. Tonnage: {row['estimated_tonnage']:,.0f} MT\n"
            f"County: {row['county']}"
        ),
        axis=1
    )
    
    logger.info("✅ Added color, radius, and tooltip columns")
    
    return df


def validate_schema(df: pd.DataFrame) -> bool:
    """
    Validate final DataFrame schema before writing.
    
    Args:
        df: DataFrame to validate
        
    Returns:
        bool: True if valid
        
    Raises:
        ETLValidationError: If validation fails
    """
    required_columns = [
        'deposit_name', 'lat', 'lon', 'minerals', 'estimated_tonnage',
        'development_status', 'county', 'details', 'color', 'radius', 'tooltip'
    ]
    
    missing = set(required_columns) - set(df.columns)
    if missing:
        raise ETLValidationError(f"Missing required columns: {missing}")
    
    # Validate data types
    if not pd.api.types.is_numeric_dtype(df['lat']):
        raise ETLValidationError("lat must be numeric")
    if not pd.api.types.is_numeric_dtype(df['lon']):
        raise ETLValidationError("lon must be numeric")
    if not pd.api.types.is_numeric_dtype(df['estimated_tonnage']):
        raise ETLValidationError("estimated_tonnage must be numeric")
    
    # Check coordinate bounds
    invalid_coords = df.apply(
        lambda row: not validate_texas_coordinates(row['lat'], row['lon']),
        axis=1
    )
    if invalid_coords.any():
        raise ETLValidationError(f"Found {invalid_coords.sum()} deposits outside Texas")
    
    logger.info(f"✅ Schema validation passed for {len(df)} deposits")
    return True


def atomic_write_parquet(df: pd.DataFrame, output_path: str) -> None:
    """
    Write DataFrame to parquet file atomically.
    
    Args:
        df: DataFrame to write
        output_path: Output file path
        
    Raises:
        ETLProcessingError: If write fails
    """
    logger.info(f"Writing {len(df)} deposits to {output_path}")
    
    try:
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        with tempfile.NamedTemporaryFile(
            mode='wb',
            suffix='.parquet',
            dir=output_dir,
            delete=False
        ) as tmp_file:
            temp_path = tmp_file.name
        
        df.to_parquet(temp_path, index=False, engine='pyarrow')
        
        # Verify write
        test_df = pd.read_parquet(temp_path)
        if len(test_df) != len(df):
            raise ETLProcessingError(
                f"Verification failed: expected {len(df)} rows, got {len(test_df)}"
            )
        
        shutil.move(temp_path, output_path)
        logger.info(f"✅ Successfully wrote mineral data to {output_path}")
        
    except Exception as e:
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.unlink(temp_path)
        logger.error(f"Failed to write parquet: {e}")
        raise ETLProcessingError(f"File write failed: {e}")


def main():
    """Main ETL execution function"""
    logger.info("=" * 60)
    logger.info("🚀 STARTING TEXAS REE & CRITICAL MINERALS ETL")
    logger.info("=" * 60)
    
    try:
        # File paths
        manual_csv_path = "data/manual_mineral_deposits.csv"
        geojson_path = "data/mineral_deposits.geojson"  # TODO: Add when available
        output_path = "data/minerals_deposits.parquet"
        
        # Load data from available sources
        logger.info("📥 Loading mineral deposit data...")
        
        # Load manual CSV (primary source)
        manual_df = load_manual_deposits(manual_csv_path)
        
        # TODO: Load GeoJSON when available
        # geojson_df = load_geojson_deposits(geojson_path)
        # combined_df = pd.concat([manual_df, geojson_df], ignore_index=True)
        
        combined_df = manual_df  # For now, just use manual data
        
        if combined_df.empty:
            logger.warning("⚠️  No deposit data found!")
            logger.info("Create data/manual_mineral_deposits.csv to add deposit data")
            logger.info("See documentation for required CSV format")
            return False
        
        # Clean and validate data
        logger.info("🧹 Cleaning and validating deposit data...")
        clean_df = clean_and_validate_deposits(combined_df)
        
        if clean_df.empty:
            logger.error("❌ No valid deposits after cleaning")
            return False
        
        # Add visualization columns
        logger.info("🎨 Adding visualization attributes...")
        final_df = add_visualization_columns(clean_df)
        
        # Add metadata
        final_df['data_source'] = 'Manual CSV + GeoJSON'
        final_df['last_updated'] = datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')
        
        # Validate final schema
        logger.info("✅ Validating final schema...")
        validate_schema(final_df)
        
        # Write output
        logger.info("💾 Writing mineral data...")
        atomic_write_parquet(final_df, output_path)
        
        # Generate polygon overlays from USGS shapefile
        logger.info("")
        logger.info("🗺️  Generating formation polygon overlays...")
        try:
            import convert_shapefile
            polygon_success = convert_shapefile.main()
            if polygon_success:
                logger.info("✅ Polygon overlay generation successful")
            else:
                logger.warning("⚠️  Polygon generation skipped (shapefile not found)")
        except Exception as e:
            logger.warning(f"⚠️  Polygon generation failed: {e}")
            logger.info("   Continuing with point data only...")
        
        # Summary statistics
        logger.info("=" * 60)
        logger.info("🎉 MINERALS ETL COMPLETED SUCCESSFULLY")
        logger.info("=" * 60)
        logger.info(f"📊 Total deposits: {len(final_df)}")
        logger.info(f"📍 By status: {final_df['development_status'].value_counts().to_dict()}")
        logger.info(f"⚡ Total estimated tonnage: {final_df['estimated_tonnage'].sum():,.0f} MT")
        logger.info(f"🗺️  Geographic coverage: {final_df['county'].nunique()} counties")
        logger.info(f"📁 Output file: {output_path}")
        logger.info(f"🕒 Last updated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        return True
        
    except (ETLValidationError, ETLProcessingError) as e:
        logger.error(f"❌ ETL process failed: {e}")
        return False
    except Exception as e:
        logger.error(f"💥 Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
