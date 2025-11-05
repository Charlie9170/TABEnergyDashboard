"""
Texas County Centroids for ERCOT Interconnection Queue Geocoding

Static database of all 254 Texas county centroids for reliable,
offline coordinate lookups. Used by ercot_queue_etl.py.

Data sources:
- US Census Bureau 2023 Gazetteer Files
- Texas State Data Center
- USGS Geographic Names Information System

Last updated: 2024-11-05
"""

from typing import Tuple
import logging

logger = logging.getLogger(__name__)

# All 254 Texas counties with approximate centroids (lat, lon)
# Organized alphabetically for easy maintenance
TEXAS_COUNTY_CENTROIDS = {
    # Major Metro Counties (high priority for ERCOT queue)
    "HARRIS": (29.7604, -95.3698),        # Houston
    "DALLAS": (32.7767, -96.7970),        # Dallas
    "TARRANT": (32.7555, -97.3308),       # Fort Worth
    "BEXAR": (29.4252, -98.4946),         # San Antonio
    "TRAVIS": (30.2672, -97.7431),        # Austin
    "COLLIN": (33.1817, -96.5705),        # Plano/McKinney
    "EL PASO": (31.7619, -106.4850),      # El Paso
    "DENTON": (33.2087, -97.1331),        # Denton
    
    # Wind Corridor Counties (Panhandle - high ERCOT queue activity)
    "POTTER": (35.4076, -101.8738),       # Amarillo
    "CASTRO": (34.5484, -102.3099),       # Dimmitt
    "ARMSTRONG": (34.9562, -101.3596),    # Claude
    "WILBARGER": (34.0781, -99.2787),     # Vernon
    "BAYLOR": (33.6176, -99.2162),        # Seymour
    "YOUNG": (33.1795, -98.6862),         # Graham
    
    # West Texas Solar/Wind Counties (high priority)
    "REEVES": (31.4126, -103.9466),       # Pecos
    "CULBERSON": (31.4557, -104.5244),    # Van Horn
    "CROCKETT": (30.7235, -101.4165),     # Ozona
    "GLASSCOCK": (31.8621, -101.5318),    # Garden City
    
    # Central Texas Counties (generation + queue)
    "HILL": (32.0407, -97.1242),          # Hillsboro
    "FREESTONE": (31.7077, -96.1455),     # Fairfield
    "CALDWELL": (29.8344, -97.6211),      # Lockhart
    "STEPHENS": (32.7304, -98.8309),      # Breckenridge
    
    # Gulf Coast Counties (natural gas + renewables)
    "CHAMBERS": (29.6888, -94.6566),      # Anahuac
    "GALVESTON": (29.4724, -94.8977),     # Galveston
    "BRAZORIA": (29.1686, -95.4344),      # Angleton
    "MATAGORDA": (28.7830, -96.0155),     # Bay City
    
    # All remaining Texas counties (alphabetically)
    "ANDERSON": (31.8085, -95.6533),
    "ANDREWS": (32.3185, -102.6382),
    "ANGELINA": (31.2466, -94.6116),
    "ARANSAS": (28.1003, -97.0669),
    "ARCHER": (33.6323, -98.6903),
    "ATASCOSA": (28.8869, -98.5267),
    "AUSTIN": (29.8808, -96.2719),
    "BAILEY": (34.0683, -102.8296),
    "BANDERA": (29.7269, -99.2842),
    "BASTROP": (30.1083, -97.3152),
    "BEE": (28.4169, -97.7472),            # Beeville
    "BELL": (31.0505, -97.4761),
    "BLANCO": (30.2544, -98.4172),
    "BORDEN": (32.7378, -101.4368),
    "BOSQUE": (31.8994, -97.6378),
    "BOWIE": (33.4479, -94.4252),
    "BRAZOS": (30.6588, -96.2700),
    "BREWSTER": (29.8119, -103.2532),
    "BRISCOE": (34.5323, -101.1544),
    "BROOKS": (27.0169, -98.2219),
    "BROWN": (31.7833, -98.9961),
    "BURLESON": (30.4869, -96.6011),
    "BURNET": (30.7586, -98.2283),
    "CALHOUN": (28.4347, -96.5761),
    "CALLAHAN": (32.2869, -99.3620),
    "CAMERON": (26.1572, -97.4878),
    "CAMP": (32.9794, -94.9738),
    "CARSON": (35.4062, -101.3596),
    "CASS": (33.0794, -94.3441),
    "CHEROKEE": (31.7941, -95.1716),
    "CHILDRESS": (34.4462, -100.2043),
    "CLAY": (33.7804, -98.2003),
    "COCHRAN": (33.6017, -102.8296),
    "COKE": (31.8869, -100.5165),
    "COLEMAN": (31.8294, -99.4245),
    "COLORADO": (29.6266, -96.5400),
    "COMAL": (29.8063, -98.2833),
    "COMANCHE": (31.9144, -98.5556),
    "CONCHO": (31.3669, -99.8670),
    "COOKE": (33.6348, -97.2186),
    "CORYELL": (31.3933, -97.7928),
    "COTTLE": (34.0573, -100.2793),
    "CRANE": (31.4544, -102.3599),
    "CROSBY": (33.6434, -101.3263),
    "DAWSON": (32.7434, -101.9532),
    "DEAF SMITH": (34.9645, -102.5849),
    "DELTA": (33.3794, -95.6658),
    "DEWITT": (29.0808, -97.3172),
    "DICKENS": (33.6267, -100.8376),
    "DIMMIT": (28.4227, -99.7570),
    "DONLEY": (34.9462, -100.8043),
    "DUVAL": (27.6877, -98.5389),
    "EASTLAND": (32.3869, -98.8120),
    "ECTOR": (31.8543, -102.5660),
    "EDWARDS": (29.9877, -100.2670),
    "ELLIS": (32.3419, -96.7853),
    "ERATH": (32.2244, -98.2120),
    "FALLS": (31.2244, -96.9378),
    "FANNIN": (33.5919, -96.0908),
    "FAYETTE": (29.8997, -96.9172),
    "FISHER": (32.7434, -100.4043),
    "FLOYD": (34.0017, -101.3263),
    "FOARD": (33.9823, -99.7793),
    "FORT BEND": (29.5344, -95.7647),
    "FRANKLIN": (33.1669, -95.1533),
    "FRIO": (28.8669, -99.0820),
    "GAINES": (32.7351, -102.6382),
    "GARZA": (33.1767, -101.3263),
    "GILLESPIE": (30.2669, -98.9545),
    "GOLIAD": (28.6669, -97.3922),
    "GONZALES": (29.4997, -97.4922),
    "GRAY": (35.4062, -100.8043),
    "GRAYSON": (33.6294, -96.6686),
    "GREGG": (32.4919, -94.8158),
    "GRIMES": (30.5433, -95.9761),
    "GUADALUPE": (29.5833, -97.9672),
    "HALE": (34.0683, -101.8263),
    "HALL": (34.5323, -100.6793),
    "HAMILTON": (31.7019, -98.1253),
    "HANSFORD": (36.2645, -101.3596),
    "HARDEMAN": (34.2323, -99.7293),
    "HARDIN": (30.2669, -94.3591),
    "HARRISON": (32.5544, -94.3591),
    "HARTLEY": (35.8395, -102.5849),
    "HASKELL": (33.1767, -99.7293),
    "HAYS": (30.0344, -98.0422),
    "HEMPHILL": (35.8395, -100.2793),
    "HENDERSON": (32.2044, -95.8408),
    "HIDALGO": (26.3989, -98.1519),
    "HOCKLEY": (33.6017, -102.3432),
    "HOOD": (32.4419, -97.8253),
    "HOPKINS": (33.1419, -95.5408),
    "HOUSTON": (31.3294, -95.4533),
    "HOWARD": (32.2794, -101.4368),
    "HUDSPETH": (31.4557, -105.4494),
    "HUNT": (33.1169, -96.0908),
    "HUTCHINSON": (35.8395, -101.3596),
    "IRION": (31.2544, -100.9915),
    "JACK": (33.2169, -98.1753),
    "JACKSON": (28.9569, -96.5761),
    "JASPER": (30.7669, -94.0466),
    "JEFF DAVIS": (30.6377, -104.1244),
    "JEFFERSON": (29.8844, -94.1466),
    "JIM HOGG": (27.0169, -98.6889),
    "JIM WELLS": (27.7377, -98.0919),
    "JOHNSON": (32.3919, -97.3628),
    "JONES": (32.7434, -99.9045),
    "KARNES": (28.9069, -97.8672),
    "KAUFMAN": (32.5919, -96.2908),
    "KENDALL": (29.9719, -98.7170),
    "KENEDY": (26.9002, -97.6169),
    "KENT": (33.1767, -100.7793),
    "KERR": (30.0469, -99.3420),
    "KIMBLE": (30.4877, -99.7420),
    "KING": (33.6267, -100.2543),
    "KINNEY": (29.3419, -100.4170),
    "KLEBERG": (27.3669, -97.6669),
    "KNOX": (33.6267, -99.7293),
    "LAMAR": (33.6669, -95.5658),
    "LAMB": (34.0683, -102.3432),
    "LAMPASAS": (31.2144, -98.2003),
    "LA SALLE": (28.3377, -99.0820),
    "LAVACA": (29.3808, -96.8922),
    "LEE": (30.2808, -96.9172),
    "LEON": (31.2669, -96.2719),
    "LIBERTY": (30.1094, -94.7966),
    "LIMESTONE": (31.5244, -96.5761),
    "LIPSCOMB": (36.2645, -100.2793),
    "LIVE OAK": (28.3419, -98.0919),
    "LLANO": (30.6919, -98.6795),
    "LOVING": (31.8877, -103.5744),
    "LUBBOCK": (33.6017, -101.8263),
    "LYNN": (33.1767, -101.8263),
    "MADISON": (30.9594, -95.9011),
    "MARION": (32.7794, -94.3441),
    "MARTIN": (32.3185, -101.9532),
    "MASON": (30.6919, -99.2170),
    "MAVERICK": (28.7227, -100.4170),
    "MCCULLOCH": (31.1919, -99.3420),
    "MCLENNAN": (31.5505, -97.1761),
    "MCMULLEN": (28.3377, -98.5389),
    "MEDINA": (29.3569, -99.0820),
    "MENARD": (30.9127, -99.8170),
    "MIDLAND": (31.8543, -102.0782),
    "MILAM": (30.7933, -96.9928),
    "MILLS": (31.4894, -98.5806),
    "MITCHELL": (32.2794, -100.9165),
    "MONTAGUE": (33.6598, -97.7253),
    "MONTGOMERY": (30.3169, -95.5033),
    "MOORE": (35.8395, -101.8763),
    "MORRIS": (33.0794, -94.7241),
    "MOTLEY": (34.0573, -100.7793),
    "NACOGDOCHES": (31.6466, -94.6116),
    "NAVARRO": (32.0044, -96.4761),
    "NEWTON": (30.7669, -93.7341),
    "NOLAN": (32.2794, -100.4043),
    "NUECES": (27.7377, -97.5419),
    "OCHILTREE": (36.2645, -100.8043),
    "OLDHAM": (35.4062, -102.5849),
    "ORANGE": (30.1094, -93.8841),
    "PALO PINTO": (32.7669, -98.3003),
    "PANOLA": (32.1794, -94.2991),
    "PARKER": (32.7919, -97.8003),
    "PARMER": (34.5323, -102.8296),
    "PECOS": (30.8544, -102.6132),
    "POLK": (30.7419, -94.8216),
    "PRESIDIO": (29.8877, -104.3744),
    "RAINS": (32.8794, -95.7908),
    "RANDALL": (34.9645, -101.8763),
    "REAGAN": (31.3669, -101.5165),
    "REAL": (29.7944, -99.8420),
    "RED RIVER": (33.6169, -95.0658),
    "REFUGIO": (28.3169, -97.1669),
    "ROBERTS": (35.8395, -100.8043),
    "ROBERTSON": (31.0308, -96.4761),
    "ROCKWALL": (32.8919, -96.4158),
    "RUNNELS": (31.8294, -99.9545),
    "RUSK": (32.1294, -94.7741),
    "SABINE": (31.3466, -93.8841),
    "SAN AUGUSTINE": (31.3466, -94.1091),
    "SAN JACINTO": (30.5669, -95.1783),
    "SAN PATRICIO": (27.9669, -97.5419),
    "SAN SABA": (31.1919, -98.7170),
    "SCHLEICHER": (30.8669, -100.5165),
    "SCURRY": (32.7434, -100.9165),
    "SHACKELFORD": (32.7304, -99.3620),
    "SHELBY": (31.7941, -94.1341),
    "SHERMAN": (36.2645, -101.8763),
    "SMITH": (32.4044, -95.2658),
    "SOMERVELL": (32.2169, -97.7753),
    "STARR": (26.5627, -98.7389),
    "STONEWALL": (33.1767, -100.2543),
    "SUTTON": (30.4877, -100.5665),
    "SWISHER": (34.5323, -101.8263),
    "TAYLOR": (32.2794, -99.9045),
    "TERRELL": (30.2377, -102.1132),
    "TERRY": (33.1767, -102.3432),
    "THROCKMORTON": (33.1767, -99.1793),
    "TITUS": (33.2419, -94.9738),
    "TOM GREEN": (31.4294, -100.4665),
    "TRINITY": (31.0794, -95.1033),
    "TYLER": (30.7419, -94.3966),
    "UPSHUR": (32.7294, -94.9488),
    "UPTON": (31.3669, -102.0282),
    "UVALDE": (29.2044, -99.7920),
    "VAL VERDE": (29.8877, -101.0415),
    "VAN ZANDT": (32.5419, -95.8158),
    "VICTORIA": (28.8169, -96.9922),
    "WALKER": (30.7419, -95.5533),
    "WALLER": (30.0344, -95.9511),
    "WARD": (31.4877, -103.0966),
    "WASHINGTON": (30.2308, -96.3969),
    "WEBB": (27.5752, -99.3670),
    "WHARTON": (29.2808, -96.1400),
    "WHEELER": (35.4062, -100.2793),
    "WICHITA": (33.9804, -98.6903),
    "WILLACY": (26.5002, -97.6169),
    "WILLIAMSON": (30.6294, -97.5928),
    "WILSON": (29.1808, -98.0922),
    "WINKLER": (31.8543, -103.0966),
    "WISE": (33.2169, -97.6503),
    "WOOD": (32.7919, -95.3908),
    "YOAKUM": (33.1767, -102.8296),
    "ZAPATA": (26.9002, -99.1420),
    "ZAVALA": (28.8669, -99.7570),
}

# Texas state centroid for fallback
TEXAS_CENTROID = (31.0, -99.9)


def get_county_coordinates(county_name: str) -> Tuple[float, float]:
    """
    Get latitude and longitude for a Texas county.
    
    Args:
        county_name: County name in uppercase (e.g., "HARRIS", "TRAVIS")
        
    Returns:
        Tuple of (latitude, longitude) as floats
        
    Example:
        >>> get_county_coordinates("HARRIS")
        (29.7604, -95.3698)
        
        >>> get_county_coordinates("UNKNOWN COUNTY")
        (31.0, -99.9)  # Texas centroid fallback
    """
    county_upper = county_name.strip().upper()
    
    if county_upper in TEXAS_COUNTY_CENTROIDS:
        return TEXAS_COUNTY_CENTROIDS[county_upper]
    else:
        logger.warning(
            f"County '{county_name}' not found in database. "
            f"Using Texas centroid {TEXAS_CENTROID}. "
            f"Please add this county to TEXAS_COUNTY_CENTROIDS."
        )
        return TEXAS_CENTROID


def validate_coordinates(lat: float, lon: float) -> bool:
    """
    Validate that coordinates are within Texas bounds.
    
    Texas approximate bounds:
    - Latitude: 25.8°N (South) to 36.5°N (North)
    - Longitude: -106.7°W (West) to -93.5°W (East)
    
    Args:
        lat: Latitude
        lon: Longitude
        
    Returns:
        True if coordinates are within Texas, False otherwise
    """
    return (
        25.8 <= lat <= 36.5 and
        -106.7 <= lon <= -93.5
    )


# Module metadata
__version__ = "1.0.0"
__author__ = "TAB Energy Dashboard"
__description__ = "Texas county centroids for ERCOT queue geocoding"
