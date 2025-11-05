"""
Quick test of ETL configuration after secrets.toml is set up
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

print("Testing ETL Configuration")
print("=" * 60)

# Test 1: Import ETL modules
print("\n1. Testing ETL module imports...")
try:
    from etl import eia_fuelmix_etl
    print("   ✅ eia_fuelmix_etl imported")
except Exception as e:
    print(f"   ❌ Failed: {e}")
    sys.exit(1)

# Test 2: Check API key loading
print("\n2. Testing API key configuration...")
try:
    api_key = eia_fuelmix_etl.get_api_key()
    if api_key and api_key != "YOUR_ACTUAL_EIA_API_KEY_HERE":
        print(f"   ✅ API key loaded: {api_key[:8]}...")
    else:
        print("   ❌ API key not configured properly")
        print("   → Edit .streamlit/secrets.toml and add your real key")
        sys.exit(1)
except Exception as e:
    print(f"   ❌ Failed: {e}")
    sys.exit(1)

# Test 3: Test API call
print("\n3. Testing live API call to EIA...")
try:
    import requests
    url = "https://api.eia.gov/v2/electricity/rto/fuel-type-data/data/"
    params = {
        'api_key': api_key,
        'frequency': 'hourly',
        'data[0]': 'value',
        'facets[respondent][]': 'ERCO',
        'start': '2025-01-01',
        'end': '2025-01-02',
        'length': 5
    }
    response = requests.get(url, params=params, timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        if 'response' in data and 'data' in data['response']:
            record_count = len(data['response']['data'])
            print(f"   ✅ API call successful!")
            print(f"   ✅ Retrieved {record_count} sample records")
            if record_count > 0:
                sample = data['response']['data'][0]
                print(f"   Sample: {sample.get('respondent')} - {sample.get('fueltype')} - {sample.get('value')}")
        else:
            print(f"   ⚠️  Unexpected response format")
            print(f"   Response: {data}")
    elif response.status_code == 403:
        print(f"   ❌ API key invalid or unauthorized (HTTP 403)")
        print("   → Check your API key at https://www.eia.gov/opendata/")
        sys.exit(1)
    else:
        print(f"   ❌ API call failed (HTTP {response.status_code})")
        print(f"   Response: {response.text[:200]}")
        sys.exit(1)
        
except Exception as e:
    print(f"   ❌ Failed: {e}")
    sys.exit(1)

# Test 4: Test data directories
print("\n4. Testing data directories...")
data_dir = Path(__file__).parent / "data"
if data_dir.exists():
    print(f"   ✅ Data directory exists: {data_dir}")
else:
    print(f"   ⚠️  Data directory missing, creating...")
    data_dir.mkdir(exist_ok=True)

print("\n" + "=" * 60)
print("✅ ALL TESTS PASSED!")
print("\nYou can now run the ETL scripts:")
print("  python etl/eia_fuelmix_etl.py")
print("  python etl/eia_plants_etl.py")
print("  python etl/ercot_queue_etl.py")
print("  python etl/price_map_etl.py")
print("=" * 60)
