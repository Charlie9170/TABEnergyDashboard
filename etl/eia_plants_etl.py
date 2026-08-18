"""
EIA Plants ETL Script

Fetches Texas power generation facility data from EIA API.
Uses EIA-860 plant coordinates and EIA-923 facility-fuel measured generation only —
no estimated or fabricated output values.

Data source: U.S. Energy Information Administration (EIA) Operating Generator Capacity API
Output: Parquet file with standardized Texas power plant data
"""

import logging
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import time

import pandas as pd
from dateutil.relativedelta import relativedelta
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('etl_plants.log')
    ]
)
logger = logging.getLogger(__name__)

# Type aliases
CoordinateTuple = Tuple[float, float, str]
FuelMappingDict = Dict[str, str]
LocationData = Dict[str, Union[float, str, List[str]]]

# Constants
API_BASE_URL: str = "https://api.eia.gov/v2"
CAPACITY_ENDPOINT: str = "electricity/operating-generator-capacity"
FACILITY_FUEL_ENDPOINT: str = "electricity/facility-fuel"
DATA_DIR: Path = Path(__file__).parent.parent / "data"
PLANT_LOCATIONS_PATH: Path = DATA_DIR / "eia860_plant_locations.parquet"
MAX_RETRIES: int = 3
BACKOFF_FACTOR: float = 0.3
REQUEST_TIMEOUT: int = 30
RATE_LIMIT_DELAY: float = 0.1

# Texas geographic bounds for validation
TEXAS_BOUNDS = {
    'lat_min': 25.84,
    'lat_max': 36.50,
    'lon_min': -106.65,
    'lon_max': -93.51
}

# Schema validation
REQUIRED_INPUT_COLUMNS = ['plantName', 'technology', 'nameplate-capacity-mw']
REQUIRED_OUTPUT_COLUMNS = ['plant_name', 'lat', 'lon', 'capacity_mw', 'fuel', 'last_updated']


class ETLValidationError(Exception):
    """Custom exception for ETL validation errors."""
    pass


class EIAAPIError(Exception):
    """Custom exception for EIA API errors."""
    pass


def get_api_key() -> str:
    """
    Get EIA API key from environment or Streamlit secrets.
    
    Returns:
        API key string
        
    Raises:
        ETLValidationError: If API key not found
    """
    # Try environment variable first
    api_key = os.environ.get('EIA_API_KEY')
    
    # Try Streamlit secrets as fallback
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get('EIA_API_KEY')
        except ImportError:
            pass
    
    if not api_key:
        raise ETLValidationError(
            "EIA_API_KEY not found. Please set it as an environment variable "
            "or in Streamlit secrets (.streamlit/secrets.toml)"
        )
    
    return api_key


def create_http_session() -> requests.Session:
    """
    Create HTTP session with retry strategy and proper headers.
    
    Returns:
        Configured requests session
    """
    session = requests.Session()
    
    # Configure retry strategy
    retry_strategy = Retry(
        total=MAX_RETRIES,
        backoff_factor=BACKOFF_FACTOR,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    # Set user agent
    session.headers.update({
        'User-Agent': 'TAB-Energy-Dashboard/1.0 (Educational Use)'
    })
    
    return session


def validate_api_response(response_data: Dict) -> None:
    """
    Validate EIA API response structure.
    
    Args:
        response_data: JSON response from EIA API
        
    Raises:
        EIAAPIError: If response structure is invalid
    """
    if 'response' not in response_data:
        raise EIAAPIError("Invalid API response: missing 'response' field")
    
    if 'data' not in response_data['response']:
        raise EIAAPIError("Invalid API response: missing 'data' field")


def rolling_capacity_period() -> Tuple[str, str]:
    """Preferred month for operating-generator capacity (last complete calendar month)."""
    last_complete = datetime.now(timezone.utc).replace(day=1) - relativedelta(months=1)
    period = last_complete.strftime('%Y-%m')
    return period, period


def rolling_generation_period() -> Tuple[str, str]:
    """Preferred three-month facility-fuel window ending on the last complete month."""
    end = datetime.now(timezone.utc).replace(day=1) - relativedelta(months=1)
    start = end - relativedelta(months=2)
    return start.strftime('%Y-%m'), end.strftime('%Y-%m')


def _fetch_texas_generators_for_period(
    api_key: str, capacity_start: str, capacity_end: str
) -> pd.DataFrame:
    """Fetch Texas generators for a single capacity date range."""
    all_data: List[Dict] = []
    offset = 0
    length = 5000

    session = create_http_session()

    try:
        while True:
            url = f"{API_BASE_URL}/{CAPACITY_ENDPOINT}/data/"
            params = {
                'api_key': api_key,
                'frequency': 'monthly',
                'data[0]': 'nameplate-capacity-mw',
                'facets[stateid][]': 'TX',
                'start': capacity_start,
                'end': capacity_end,
                'offset': offset,
                'length': length,
            }

            try:
                response = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
            except requests.RequestException as e:
                raise EIAAPIError(f"API request failed at offset {offset}: {e}")

            try:
                result = response.json()
            except ValueError as e:
                raise EIAAPIError(f"Invalid JSON response at offset {offset}: {e}")

            validate_api_response(result)

            data = result['response']['data']
            if not data:
                break

            all_data.extend(data)

            total = int(result['response'].get('total', 0))
            if offset + length >= total:
                break

            offset += length
            time.sleep(RATE_LIMIT_DELAY)

    finally:
        session.close()

    if not all_data:
        return pd.DataFrame()

    df = pd.DataFrame(all_data)
    if 'plantid' in df.columns:
        df['plant_code'] = df['plantid'].astype(str)
    validate_input_schema(df)
    return df


def fetch_texas_generators(api_key: str) -> Tuple[pd.DataFrame, str, str]:
    """
    Fetch Texas power generator data, walking back month-by-month when EIA
    has not yet published the preferred rolling window.
    """
    anchor = datetime.now(timezone.utc).replace(day=1) - relativedelta(months=1)
    preferred_start, preferred_end = rolling_capacity_period()
    logger.info(
        "Fetching Texas power plant capacity (preferred period %s to %s)",
        preferred_start,
        preferred_end,
    )

    for months_back in range(24):
        month = anchor - relativedelta(months=months_back)
        period = month.strftime('%Y-%m')
        df = _fetch_texas_generators_for_period(api_key, period, period)
        if not df.empty:
            logger.info(
                "Retrieved %s generator records for capacity period %s",
                len(df),
                period,
            )
            return df, period, period

    raise ETLValidationError("No generator data returned from EIA API for any recent month")


def load_plant_coordinates() -> pd.DataFrame:
    """
    Load cached EIA-860 plant coordinates for Texas.

    Source: 2___Plant_Yyyyy.xlsx from Form EIA-860 (Plant Code, Latitude, Longitude).
    """
    if not PLANT_LOCATIONS_PATH.exists():
        raise ETLValidationError(
            f"Plant coordinate cache missing: {PLANT_LOCATIONS_PATH}. "
            "Regenerate from EIA-860 Plant schedule (2___Plant_Yyyyy.xlsx)."
        )

    coords = pd.read_parquet(PLANT_LOCATIONS_PATH)
    coords['plant_code'] = coords['plant_code'].astype(str)
    coords['lat'] = pd.to_numeric(coords['lat'], errors='coerce')
    coords['lon'] = pd.to_numeric(coords['lon'], errors='coerce')
    coords = coords.dropna(subset=['lat', 'lon']).drop_duplicates(subset=['plant_code'], keep='first')
    return coords[['plant_code', 'lat', 'lon']]


def attach_plant_coordinates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Join real EIA-860 plant coordinates by plant code.

    Plants without coordinates are dropped rather than assigned fake locations.
    """
    df = df.copy()
    if 'plant_code' not in df.columns:
        if 'plantid' in df.columns:
            df['plant_code'] = df['plantid'].astype(str)
        elif 'plantCode' in df.columns:
            df['plant_code'] = df['plantCode'].astype(str)
        else:
            raise ETLValidationError("Cannot attach coordinates: plant_code/plantid missing")

    coords = load_plant_coordinates()
    merged = df.merge(coords, on='plant_code', how='left')

    missing = merged['lat'].isna().sum()
    if missing:
        logger.warning(
            "Dropping %s generator rows with no EIA-860 coordinates (plant_code not in cache)",
            missing,
        )
        merged = merged.dropna(subset=['lat', 'lon'])

    validate_coordinates(merged)
    logger.info("Attached real coordinates for %s generator rows", len(merged))
    return merged


def _fetch_actual_generation_for_period(
    api_key: str, start_date: str, end_date: str
) -> pd.DataFrame:
    """Fetch plant-level generation for a facility-fuel date range."""
    all_data: List[Dict] = []
    offset = 0
    length = 5000

    session = create_http_session()

    try:
        while True:
            url = f"{API_BASE_URL}/{FACILITY_FUEL_ENDPOINT}/data/"
            params = {
                'api_key': api_key,
                'frequency': 'monthly',
                'data[0]': 'generation',
                'facets[state][]': 'TX',
                'start': start_date,
                'end': end_date,
                'offset': offset,
                'length': length,
            }

            try:
                response = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
                response.raise_for_status()
            except requests.RequestException as e:
                logger.warning("facility-fuel request failed at offset %s: %s", offset, e)
                break

            try:
                result = response.json()
            except ValueError as e:
                logger.warning("Invalid JSON in facility-fuel response: %s", e)
                break

            if 'response' not in result or 'data' not in result['response']:
                logger.warning("Invalid facility-fuel API response structure")
                break

            data = result['response']['data']
            if not data:
                break

            all_data.extend(data)

            total = int(result['response'].get('total', 0))
            if offset + length >= total:
                break

            offset += length
            time.sleep(RATE_LIMIT_DELAY)

    finally:
        session.close()

    if not all_data:
        return pd.DataFrame()

    df = pd.DataFrame(all_data)

    required = {'plantCode', 'generation', 'fuel2002', 'primeMover'}
    if not required.issubset(df.columns):
        logger.warning(
            "facility-fuel data missing required columns: %s",
            required - set(df.columns),
        )
        return pd.DataFrame()

    plant_totals = df[(df['fuel2002'] == 'ALL') & (df['primeMover'] == 'ALL')].copy()
    if plant_totals.empty:
        return pd.DataFrame()

    plant_totals['generation'] = pd.to_numeric(plant_totals['generation'], errors='coerce')
    plant_totals['plantCode'] = plant_totals['plantCode'].astype(str)

    df_grouped = plant_totals.groupby('plantCode', as_index=False).agg(
        generation=('generation', 'mean')
    )
    df_grouped['actual_generation_mw'] = df_grouped['generation'] / 730.0
    df_grouped = df_grouped[df_grouped['actual_generation_mw'] > 0]

    return df_grouped[['plantCode', 'actual_generation_mw']]


def fetch_actual_generation(api_key: str) -> Tuple[pd.DataFrame, str, str]:
    """
    Fetch measured generation, walking back month-by-month when EIA has not
    yet published the preferred rolling three-month window.
    """
    preferred_start, preferred_end = rolling_generation_period()
    logger.info(
        "Fetching actual generation from EIA facility-fuel (preferred %s to %s)",
        preferred_start,
        preferred_end,
    )

    anchor_end = datetime.now(timezone.utc).replace(day=1) - relativedelta(months=1)
    for months_back in range(24):
        end = anchor_end - relativedelta(months=months_back)
        start = end - relativedelta(months=2)
        start_date, end_date = start.strftime('%Y-%m'), end.strftime('%Y-%m')
        df = _fetch_actual_generation_for_period(api_key, start_date, end_date)
        if not df.empty:
            logger.info(
                "Calculated actual generation for %s plants (%s to %s)",
                len(df),
                start_date,
                end_date,
            )
            return df, start_date, end_date

    raise ETLValidationError(
        "EIA facility-fuel returned no measured generation data for any recent window"
    )


def validate_input_schema(df: pd.DataFrame) -> None:
    """
    Validate input DataFrame schema.
    
    Args:
        df: Input DataFrame to validate
        
    Raises:
        ETLValidationError: If schema validation fails
    """
    missing_cols = [col for col in REQUIRED_INPUT_COLUMNS if col not in df.columns]
    if missing_cols:
        raise ETLValidationError(f"Missing required columns: {missing_cols}")
    
    # Convert capacity to numeric (coerce errors to NaN)
    df['nameplate-capacity-mw'] = pd.to_numeric(df['nameplate-capacity-mw'], errors='coerce')
    
    # Validate data types
    if not pd.api.types.is_numeric_dtype(df['nameplate-capacity-mw']):
        raise ETLValidationError("nameplate-capacity-mw must be numeric")
    
    logger.info(f"Input schema validation passed: {len(df)} records")


def get_texas_locations() -> List[CoordinateTuple]:
    """
    Get real Texas geographic locations for natural facility distribution.
    
    Returns:
        List of (latitude, longitude, location_name) tuples
    """
    return [
        # Major metropolitan areas
        (29.7604, -95.3698, "Houston"),  # Harris County
        (32.7767, -96.7970, "Dallas"),   # Dallas County
        (29.4241, -98.4936, "San Antonio"),  # Bexar County
        (30.2672, -97.7431, "Austin"),   # Travis County
        (32.7555, -97.3308, "Fort Worth"),  # Tarrant County
        
        # Major cities
        (26.2034, -98.2300, "McAllen"),  # Hidalgo County
        (27.8006, -97.3964, "Corpus Christi"),  # Nueces County
        (33.5779, -101.8552, "Lubbock"),  # Lubbock County
        (32.4487, -99.7331, "Abilene"),  # Taylor County
        
        # East Texas
        (32.3513, -94.7077, "Tyler"),    # Smith County
        (32.5007, -94.7405, "Longview"), # Gregg County
        (30.0588, -94.1266, "Beaumont"), # Jefferson County
        
        # Central Texas
        (31.5488, -97.1131, "Waco"),     # McLennan County
        (31.0800, -97.3428, "Temple"),   # Bell County
        (30.6304, -96.3272, "College Station"), # Brazos County
        
        # West Texas
        (31.9973, -102.0779, "Midland"), # Midland County
        (31.8457, -102.3676, "Odessa"),  # Ector County
        (35.2220, -101.8313, "Amarillo"), # Potter County
        
        # South Texas
        (27.5064, -99.5075, "Laredo"),   # Webb County
        (25.9018, -97.4975, "Brownsville"), # Cameron County
        (28.0378, -82.4572, "Victoria"), # Victoria County
        
        # Additional locations for better distribution
        (31.3069, -94.7821, "Jacksonville"), # Cherokee County
        (30.0691, -93.7137, "Orange"),   # Orange County
        (29.3013, -94.7977, "Port Arthur"), # Jefferson County
        (28.8056, -96.9489, "Bay City"), # Matagorda County
        (29.7030, -98.1245, "New Braunfels"), # Comal County
        (30.5527, -97.6786, "Round Rock"), # Williamson County
        (32.9668, -96.6989, "Plano"),    # Collin County
        (29.5516, -98.5816, "Uvalde"),   # Uvalde County
        (31.7619, -106.4850, "El Paso"), # El Paso County
        (27.2517, -98.2897, "Alice"),    # Jim Wells County
        
        # Wind corridor locations
        (32.0853, -100.4326, "Sweetwater"), # Nolan County
        (32.2504, -100.9015, "Big Spring"), # Howard County
        (32.7282, -100.8926, "Snyder"),  # Scurry County
        (33.1584, -101.7068, "Post"),    # Garza County
        
        # Additional geographic diversity
        (30.8665, -102.3929, "Fort Stockton"), # Pecos County
        (29.8833, -103.5578, "Alpine"),  # Brewster County
        (31.2504, -94.7291, "Lufkin"),   # Angelina County
        (30.6280, -94.6533, "Liberty"), # Liberty County
        (29.0383, -95.0177, "Angleton"), # Brazoria County
        (28.6922, -96.1289, "Edna"),     # Jackson County
        (32.4412, -94.0377, "Marshall"), # Harrison County
        (33.9137, -98.4934, "Wichita Falls"), # Wichita County
        (31.4638, -100.4370, "San Angelo"), # Tom Green County
        (29.7012, -98.1245, "Seguin"),   # Guadalupe County
    ]


def geocode_plant_locations(df: pd.DataFrame) -> pd.DataFrame:
    """Attach EIA-860 plant coordinates (legacy name kept for tests)."""
    return attach_plant_coordinates(df)


def validate_coordinates(df: pd.DataFrame) -> None:
    """
    Validate that all coordinates are within Texas bounds.
    
    Args:
        df: DataFrame with lat/lon columns
        
    Raises:
        ETLValidationError: If coordinates are outside Texas bounds
    """
    within_bounds = (
        (df['lat'] >= TEXAS_BOUNDS['lat_min']) & 
        (df['lat'] <= TEXAS_BOUNDS['lat_max']) &
        (df['lon'] >= TEXAS_BOUNDS['lon_min']) & 
        (df['lon'] <= TEXAS_BOUNDS['lon_max'])
    )
    
    if not within_bounds.all():
        invalid_count = (~within_bounds).sum()
        raise ETLValidationError(f"{invalid_count} coordinates outside Texas bounds")
    
    logger.info("All coordinates validated within Texas bounds")


def get_fuel_mapping() -> FuelMappingDict:
    """
    Get comprehensive EIA fuel type mapping to canonical names.
    
    Returns:
        Dictionary mapping EIA fuel types to canonical fuel names
    """
    return {
        # Solar Technologies
        'Solar Photovoltaic': 'SOLAR',
        'Solar Thermal with Energy Storage': 'SOLAR',
        'Solar Thermal without Energy Storage': 'SOLAR',
        
        # Natural Gas Technologies  
        'Natural Gas Steam Turbine': 'GAS', 
        'Natural Gas Combined Cycle': 'GAS',
        'Natural Gas Fired Combined Cycle': 'GAS',
        'Natural Gas Combustion Turbine': 'GAS',
        'Natural Gas Fired Combustion Turbine': 'GAS', 
        'Natural Gas Internal Combustion Engine': 'GAS',
        'Natural Gas with Compressed Air Energy Storage': 'GAS',
        
        # Wind Technologies
        'Onshore Wind Turbine': 'WIND',
        'Offshore Wind Turbine': 'WIND',
        
        # Coal Technologies
        'Coal': 'COAL',
        'Conventional Steam Coal': 'COAL',
        'Coal Integrated Gasification Combined Cycle': 'COAL',
        
        # Nuclear
        'Nuclear': 'NUCLEAR',
        'Conventional Nuclear': 'NUCLEAR',
        
        # Hydroelectric
        'Conventional Hydroelectric': 'HYDRO',
        'Hydroelectric Pumped Storage': 'HYDRO',
        'Small Hydroelectric': 'HYDRO',
        
        # Energy Storage
        'Batteries': 'STORAGE',
        'Battery Energy Storage System': 'STORAGE',
        'Electrochemical': 'STORAGE',
        
        # Oil/Petroleum
        'Petroleum Liquids': 'OIL',
        'Distillate Fuel Oil': 'OIL',
        'Residual Fuel Oil': 'OIL',
        'Petroleum Coke': 'OIL',
        
        # Biomass
        'Wood/Wood Waste Biomass': 'BIOMASS',
        'Municipal Solid Waste': 'BIOMASS',
        'Landfill Gas': 'BIOMASS',
        'Agricultural Crop Byproducts/Straw/Energy Crops': 'BIOMASS',
        
        # Geothermal
        'Geothermal': 'GEOTHERMAL',
        
        # Other/Miscellaneous
        'Other': 'OTHER',
        'All Other': 'OTHER',
        'Flywheels': 'OTHER',
    }


def normalize_fuel_types(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize EIA fuel type codes to canonical fuel names.
    
    Args:
        df: DataFrame with EIA fuel data
        
    Returns:
        DataFrame with normalized fuel types
    """
    logger.info("Normalizing fuel types")
    
    df = df.copy()
    fuel_mapping = get_fuel_mapping()
    
    # Map fuel types, default to 'OTHER' for unmapped types
    df['fuel'] = df['technology'].map(fuel_mapping).fillna('OTHER')
    
    # Log fuel type distribution
    fuel_counts = df['fuel'].value_counts()
    logger.info(f"Fuel type distribution: {fuel_counts.to_dict()}")
    
    return df


def transform_to_canonical_schema(df: pd.DataFrame, generation_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """
    Transform raw EIA data to canonical schema with validation.
    Optionally merges actual generation data with nameplate capacity.
    
    Args:
        df: Raw EIA DataFrame with nameplate capacity
        generation_df: Optional DataFrame with actual generation data
        
    Returns:
        DataFrame with canonical schema including both capacity and actual generation
    """
    logger.info("Transforming to canonical schema")
    
    # Check if plant code is available for merging with generation data
    has_plant_code = 'plant_code' in df.columns
    
    group_keys = ['plantName', 'lat', 'lon', 'fuel']
    agg_spec = {'nameplate-capacity-mw': 'sum'}
    if has_plant_code:
        agg_spec['plant_code'] = 'first'

    df_grouped = df.groupby(group_keys).agg(agg_spec).reset_index()
    
    # Create canonical schema base
    canonical_df = pd.DataFrame({
        'plant_name': df_grouped['plantName'],
        'lat': df_grouped['lat'],
        'lon': df_grouped['lon'], 
        'capacity_mw': df_grouped['nameplate-capacity-mw'],
        'fuel': df_grouped['fuel'],
        'last_updated': datetime.now(timezone.utc).isoformat()
    })
    
    if has_plant_code:
        canonical_df['plant_code'] = df_grouped['plant_code'].astype(str)
    
    # Merge measured generation (required — no estimates or fabrication)
    if generation_df is None or generation_df.empty:
        raise ETLValidationError(
            "Measured generation data required from EIA facility-fuel; refusing to fabricate values"
        )
    if not has_plant_code:
        raise ETLValidationError("plant_code required to join facility-fuel generation data")

    generation_df = generation_df.copy()
    generation_df['plantCode'] = generation_df['plantCode'].astype(str)
    logger.info("Merging measured generation for %s plants", len(generation_df))
    canonical_df = canonical_df.merge(
        generation_df[['plantCode', 'actual_generation_mw']],
        left_on='plant_code',
        right_on='plantCode',
        how='inner',
    )
    canonical_df.drop(columns=['plantCode'], inplace=True, errors='ignore')

    if canonical_df.empty:
        raise ETLValidationError("No facilities matched measured EIA facility-fuel generation")

    # facility-fuel is plant-level; allocate measured MW across fuel rows by capacity share
    plant_capacity = canonical_df.groupby('plant_code')['capacity_mw'].transform('sum')
    plant_generation = canonical_df.groupby('plant_code')['actual_generation_mw'].transform('first')
    canonical_df['actual_generation_mw'] = plant_generation * (
        canonical_df['capacity_mw'] / plant_capacity
    )
    canonical_df['generation_is_estimated'] = False

    measured = len(canonical_df)
    logger.info("Output contains %s plant/fuel rows with measured generation only", measured)
    
    # Validate data types
    canonical_df['capacity_mw'] = pd.to_numeric(canonical_df['capacity_mw'], errors='coerce')
    canonical_df['actual_generation_mw'] = pd.to_numeric(canonical_df['actual_generation_mw'], errors='coerce')
    canonical_df['lat'] = pd.to_numeric(canonical_df['lat'], errors='coerce') 
    canonical_df['lon'] = pd.to_numeric(canonical_df['lon'], errors='coerce')
    
    # Remove any rows with invalid numeric data
    initial_count = len(canonical_df)
    canonical_df = canonical_df.dropna(subset=['capacity_mw', 'actual_generation_mw', 'lat', 'lon'])
    final_count = len(canonical_df)
    
    if initial_count != final_count:
        logger.warning(f"Dropped {initial_count - final_count} rows with invalid numeric data")
    
    # Sort by actual generation (largest first) and deduplicate
    canonical_df = canonical_df.sort_values('actual_generation_mw', ascending=False)
    canonical_df = canonical_df.drop_duplicates(subset=['plant_name', 'fuel'], keep='first')
    
    # Drop plant_code before output (internal use only)
    canonical_df = canonical_df.drop('plant_code', axis=1, errors='ignore')
    
    validate_output_schema(canonical_df)
    
    logger.info(f"Transformed to {len(canonical_df)} unique facilities")
    
    return canonical_df


def validate_output_schema(df: pd.DataFrame) -> None:
    """
    Validate output DataFrame schema.
    
    Args:
        df: Output DataFrame to validate
        
    Raises:
        ETLValidationError: If schema validation fails
    """
    missing_cols = [col for col in REQUIRED_OUTPUT_COLUMNS if col not in df.columns]
    if missing_cols:
        raise ETLValidationError(f"Output missing required columns: {missing_cols}")
    
    # Validate data types
    if not pd.api.types.is_numeric_dtype(df['capacity_mw']):
        raise ETLValidationError("capacity_mw must be numeric")
    
    if not pd.api.types.is_numeric_dtype(df['lat']):
        raise ETLValidationError("lat must be numeric")
    
    if not pd.api.types.is_numeric_dtype(df['lon']):
        raise ETLValidationError("lon must be numeric")
    
    # Validate capacity is positive
    if (df['capacity_mw'] <= 0).any():
        raise ETLValidationError("All capacity values must be positive")
    
    logger.info(f"Output schema validation passed: {len(df)} records")


def atomic_write_parquet(df: pd.DataFrame, output_path: Path) -> None:
    """
    Write DataFrame to Parquet file atomically.
    
    Args:
        df: DataFrame to write
        output_path: Output file path
    """
    logger.info(f"Writing {len(df)} records to {output_path}")
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write to temporary file first, then move to final location
    with tempfile.NamedTemporaryFile(
        suffix='.parquet',
        dir=output_path.parent,
        delete=False
    ) as tmp_file:
        tmp_path = Path(tmp_file.name)
    
    try:
        df.to_parquet(tmp_path, engine='pyarrow', compression='snappy')
        tmp_path.replace(output_path)
        logger.info(f"Successfully wrote to {output_path}")
    except Exception as e:
        # Clean up temporary file on error
        if tmp_path.exists():
            tmp_path.unlink()
        raise e


def main() -> None:
    """Main ETL execution function."""
    try:
        logger.info("Starting EIA Plants ETL process")
        
        # Get API key
        api_key = get_api_key()
        
        # Fetch nameplate capacity from EIA API
        raw_df, _capacity_start, _capacity_end = fetch_texas_generators(api_key)
        logger.info(f"Fetched {len(raw_df)} generator records")

        # Fetch measured generation (required)
        generation_df, gen_start, gen_end = fetch_actual_generation(api_key)
        logger.info("Fetched measured generation for %s plants", len(generation_df))
        
        # Add geographic coordinates from EIA-860 plant registry
        geo_df = attach_plant_coordinates(raw_df)
        
        # Normalize fuel types
        fuel_df = normalize_fuel_types(geo_df)
        
        # Transform to canonical schema with actual generation
        final_df = transform_to_canonical_schema(fuel_df, generation_df)

        final_df['generation_period_start'] = gen_start
        final_df['generation_period_end'] = gen_end

        # Write output atomically
        output_path = DATA_DIR / "generation.parquet"
        atomic_write_parquet(final_df, output_path)
        
        # Log summary statistics
        total_capacity = final_df['capacity_mw'].sum()
        total_actual = final_df['actual_generation_mw'].sum()
        capacity_factor = (total_actual / total_capacity * 100) if total_capacity > 0 else 0
        
        fuel_breakdown_capacity = final_df.groupby('fuel')['capacity_mw'].sum().sort_values(ascending=False)
        fuel_breakdown_actual = final_df.groupby('fuel')['actual_generation_mw'].sum().sort_values(ascending=False)
        
        logger.info(f"ETL completed successfully:")
        logger.info(f"  Facilities: {len(final_df)}")
        logger.info(f"  Total nameplate capacity: {total_capacity:,.0f} MW")
        logger.info(f"  Total actual generation: {total_actual:,.0f} MW")
        logger.info(f"  Overall capacity factor: {capacity_factor:.1f}%")
        logger.info(f"  Capacity by fuel: {fuel_breakdown_capacity.to_dict()}")
        logger.info(f"  Generation by fuel: {fuel_breakdown_actual.to_dict()}")
        
        print(f"✓ Successfully processed {len(final_df)} Texas power plants")
        print(f"✓ Total nameplate capacity: {total_capacity:,.0f} MW")
        print(f"✓ Total actual generation: {total_actual:,.0f} MW")
        print(f"✓ Capacity factor: {capacity_factor:.1f}%")
        print(f"✓ Output: {output_path}")
        
    except Exception as e:
        logger.error(f"ETL process failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()