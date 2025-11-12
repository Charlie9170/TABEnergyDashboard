#!/usr/bin/env python3
"""
USGS MRDS Shapefile to GeoJSON Converter

Converts USGS Mineral Resources Data System (MRDS) shapefiles to GeoJSON format
for display on the TAB Energy Dashboard Minerals tab.

Features:
- Reads .shp files with mineral deposit data
- Converts geometries to GeoJSON polygons
- Maps MRDS development status to TAB categories
- Assigns TAB brand colors with transparency
- Handles both polygon and point geometries

Usage:
    python etl/convert_shapefile.py

Author: TAB Energy Dashboard
Date: 2025-11-10
"""

import shapefile
import json
from pathlib import Path
import logging
import sys
from typing import Dict, List, Tuple

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# TAB Brand Colors with 25% transparency for formation overlays
FORMATION_COLORS = {
    'Major': [200, 16, 46, 64],        # TAB Red, 25% opacity
    'Early': [255, 140, 0, 64],        # Orange, 25% opacity
    'Exploratory': [241, 196, 15, 64], # Gold, 25% opacity
    'Discovery': [27, 54, 93, 64]      # TAB Navy, 25% opacity
}


def determine_status(properties: Dict) -> str:
    """
    Determine development status from MRDS shapefile attributes.
    
    Maps MRDS DEV_STAT field to TAB development categories:
    - PRODUCER → Major (active large-scale operations)
    - PAST PRODUCER/DEVELOPMENT → Early (initial production)
    - OCCURRENCE/PROSPECT → Exploratory (feasibility studies)
    - Default → Discovery (initial identification)
    
    Args:
        properties: Dictionary of shapefile record attributes
        
    Returns:
        Development status string (Major, Early, Exploratory, Discovery)
    """
    # Check common MRDS field names
    dev_status = str(properties.get('DEV_STAT', '')).upper()
    dep_type = str(properties.get('DEP_TYPE', '')).upper()
    
    # Major: Active production
    if any(x in dev_status for x in ['PRODUCER', 'PRODUCTION', 'OPERATING']):
        if 'PAST' not in dev_status:
            return 'Major'
    
    # Early: Past production or development stage
    if any(x in dev_status for x in ['PAST PRODUCER', 'DEVELOPMENT', 'ADVANCED']):
        return 'Early'
    
    # Exploratory: Occurrences or prospects with drilling
    if any(x in dev_status for x in ['OCCURRENCE', 'PROSPECT', 'EXPLORATION']):
        return 'Exploratory'
    
    # Discovery: Default for identified but undeveloped
    return 'Discovery'


def get_mineral_name(properties: Dict) -> str:
    """Extract mineral/commodity name from shapefile properties."""
    # Try common MRDS field names
    for field in ['COMMOD1', 'COMMODITY', 'DEPOSIT', 'NAME', 'SITE_NAME']:
        if field in properties and properties[field]:
            return str(properties[field])
    return 'Unknown Mineral'


def get_tonnage(properties: Dict) -> float:
    """Extract tonnage estimate from shapefile properties."""
    # Try common tonnage fields
    for field in ['ORE_TONN', 'TONNAGE', 'RESOURCES']:
        if field in properties:
            try:
                value = properties[field]
                if value and value != 'None':
                    return float(value)
            except (ValueError, TypeError):
                continue
    return 0.0


def simplify_polygon(coordinates: List[Tuple[float, float]], tolerance: float = 0.01) -> List[Tuple[float, float]]:
    """
    Simplify polygon coordinates to reduce file size.
    
    Uses Douglas-Peucker algorithm approximation.
    
    Args:
        coordinates: List of (lon, lat) tuples
        tolerance: Simplification tolerance in degrees
        
    Returns:
        Simplified coordinate list
    """
    if len(coordinates) < 10:
        return coordinates  # Don't simplify small polygons
    
    # Keep every Nth point based on polygon size
    step = max(1, len(coordinates) // 50)  # Max 50 points per polygon
    simplified = coordinates[::step]
    
    # Always include first and last point
    if simplified[0] != coordinates[0]:
        simplified.insert(0, coordinates[0])
    if simplified[-1] != coordinates[-1]:
        simplified.append(coordinates[-1])
    
    return simplified


def convert_usgs_shapefile_to_geojson(shapefile_path: str, simplify: bool = True) -> Dict:
    """
    Convert USGS MRDS shapefile to GeoJSON format.
    
    Args:
        shapefile_path: Path to .shp file (without extension)
        simplify: Whether to simplify complex polygons (reduces file size)
        
    Returns:
        GeoJSON FeatureCollection dictionary
        
    Raises:
        FileNotFoundError: If shapefile doesn't exist
        Exception: If shapefile cannot be read
    """
    shp_file = Path(shapefile_path).with_suffix('.shp')
    
    if not shp_file.exists():
        raise FileNotFoundError(f"Shapefile not found: {shp_file}")
    
    logger.info(f"Reading shapefile: {shp_file}")
    
    try:
        sf = shapefile.Reader(str(shp_file))
    except Exception as e:
        logger.error(f"Failed to read shapefile: {e}")
        raise
    
    # Get field names for properties
    fields = [field[0] for field in sf.fields[1:]]  # Skip deletion flag field
    logger.info(f"Found {len(fields)} attribute fields")
    
    features = []
    skipped_count = 0
    
    for idx, shape_record in enumerate(sf.shapeRecords()):
        shape = shape_record.shape  # type: ignore
        record = shape_record.record  # type: ignore
        
        # Create properties dictionary from record
        properties = {}
        for i, field in enumerate(fields):
            try:
                properties[field] = record[i]  # type: ignore
            except IndexError:
                properties[field] = None
        
        # Extract key attributes
        status = determine_status(properties)
        mineral_name = get_mineral_name(properties)
        tonnage = get_tonnage(properties)
        
        # Enhanced properties for dashboard
        properties['status'] = status
        properties['color'] = FORMATION_COLORS[status]
        properties['name'] = mineral_name
        properties['mineral_type'] = mineral_name
        properties['tonnage_mt'] = tonnage
        properties['description'] = f"{status} development - {mineral_name}"
        
        # Convert shapefile geometry to GeoJSON
        try:
            if shape.shapeType == 5:  # type: ignore  # Polygon
                coords = shape.points  # type: ignore
                if simplify and len(coords) > 100:
                    coords = simplify_polygon(coords)  # type: ignore
                
                # GeoJSON requires [lon, lat] format and closed rings
                if coords[0] != coords[-1]:
                    coords.append(coords[0])  # type: ignore
                
                coordinates = [coords]
                
            elif shape.shapeType == 1:  # type: ignore  # Point - convert to small polygon (0.05 degree buffer)
                lon, lat = shape.points[0][:2]  # type: ignore  # Take only lon, lat (ignore Z/M)
                buffer = 0.05
                coordinates = [[
                    [lon - buffer, lat - buffer],
                    [lon + buffer, lat - buffer],
                    [lon + buffer, lat + buffer],
                    [lon - buffer, lat + buffer],
                    [lon - buffer, lat - buffer]
                ]]
                
            elif shape.shapeType in [3, 13]:  # type: ignore  # Polyline - buffer to polygon
                coords = shape.points  # type: ignore
                if simplify and len(coords) > 50:
                    coords = simplify_polygon(coords, tolerance=0.02)  # type: ignore
                
                # Create buffered polygon around line
                buffer = 0.02
                buffered = []
                for point in coords:
                    lon, lat = point[:2]  # type: ignore  # Take only lon, lat
                    buffered.extend([
                        [lon - buffer, lat - buffer],
                        [lon + buffer, lat + buffer]
                    ])
                if buffered[0] != buffered[-1]:
                    buffered.append(buffered[0])
                coordinates = [buffered]
                
            else:
                logger.warning(f"Skipping feature {idx}: Unsupported shape type {shape.shapeType}")  # type: ignore
                skipped_count += 1
                continue
            
            # Filter to Texas bounds
            # Check if any point is within Texas
            in_texas = False
            for coord_ring in coordinates:
                for coord in coord_ring:
                    lon, lat = coord[:2] if len(coord) > 2 else coord  # type: ignore  # Handle both 2D and 3D coords
                    if -106.65 <= lon <= -93.51 and 25.84 <= lat <= 36.50:
                        in_texas = True
                        break
                if in_texas:
                    break
            
            if not in_texas:
                skipped_count += 1
                continue
            
            feature = {
                'type': 'Feature',
                'properties': properties,
                'geometry': {
                    'type': 'Polygon',
                    'coordinates': coordinates
                }
            }
            features.append(feature)
            
        except Exception as e:
            logger.warning(f"Failed to process feature {idx}: {e}")
            skipped_count += 1
            continue
    
    geojson = {
        'type': 'FeatureCollection',
        'features': features
    }
    
    logger.info(f"✅ Converted {len(features)} features to GeoJSON")
    if skipped_count > 0:
        logger.info(f"   Skipped {skipped_count} features (outside Texas or unsupported geometry)")
    
    return geojson


def main():
    """Convert USGS shapefile to GeoJSON for dashboard."""
    logger.info("=" * 60)
    logger.info("USGS MRDS Shapefile Converter - Starting")
    logger.info("=" * 60)
    
    # Path to downloaded shapefile
    # User should place shapefile in Downloads folder or update this path
    shapefile_paths = [
        Path.home() / "Downloads" / "Texas Lithium Shapefile" / "mrds-trim",
        Path.home() / "Downloads" / "mrds-trim",
        Path(__file__).parent.parent / "data" / "mrds-trim",
    ]
    
    shapefile_path = None
    for path in shapefile_paths:
        if path.with_suffix('.shp').exists():
            shapefile_path = path
            break
    
    if not shapefile_path:
        logger.error("❌ Shapefile not found!")
        logger.info("\nPlease download USGS MRDS shapefile and place it at:")
        logger.info("   ~/Downloads/Texas Lithium Shapefile/mrds-trim.shp")
        logger.info("\nOr update the path in this script.")
        return False
    
    try:
        # Convert to GeoJSON
        geojson = convert_usgs_shapefile_to_geojson(str(shapefile_path), simplify=True)
        
        # Save to data directory
        output_path = Path(__file__).parent.parent / "data" / "mineral_polygons.json"
        output_path.parent.mkdir(exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(geojson, f, indent=2)
        
        file_size_kb = output_path.stat().st_size / 1024
        
        logger.info("=" * 60)
        logger.info("✅ Conversion Complete!")
        logger.info("=" * 60)
        logger.info(f"Output file:     {output_path}")
        logger.info(f"Total features:  {len(geojson['features'])}")
        logger.info(f"File size:       {file_size_kb:.1f} KB")
        
        # Status breakdown
        status_counts = {}
        for feature in geojson['features']:
            status = feature['properties']['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        logger.info("\nBy development status:")
        for status, count in sorted(status_counts.items()):
            logger.info(f"  {status:15s} {count:4d} formations")
        
        return True
        
    except FileNotFoundError as e:
        logger.error(f"❌ {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Conversion failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
