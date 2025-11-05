"""
ETL Diagnostic Script
Checks all components needed for ETL workflows to run
"""

import sys
from pathlib import Path

print("=" * 60)
print("ETL WORKFLOW DIAGNOSTIC REPORT")
print("=" * 60)
print()

# 1. Python Version
print("1. PYTHON ENVIRONMENT")
print(f"   Python: {sys.version}")
print()

# 2. Required Packages
print("2. REQUIRED PACKAGES")
packages = {
    'pandas': 'Data processing',
    'requests': 'API calls',
    'openpyxl': 'Excel file handling',
    'pyarrow': 'Parquet file format',
    'streamlit': 'Streamlit framework'
}

for pkg, desc in packages.items():
    try:
        __import__(pkg)
        print(f"   ✅ {pkg:12} - {desc}")
    except ImportError:
        print(f"   ❌ {pkg:12} - MISSING! Install: pip install {pkg}")
print()

# 3. Check directories
print("3. DIRECTORY STRUCTURE")
base_dir = Path(__file__).parent
data_dir = base_dir / "data"
etl_dir = base_dir / "etl"
streamlit_dir = base_dir / ".streamlit"

for dir_path, name in [(data_dir, "data"), (etl_dir, "etl"), (streamlit_dir, ".streamlit")]:
    if dir_path.exists():
        print(f"   ✅ {name:12} - {dir_path}")
    else:
        print(f"   ❌ {name:12} - NOT FOUND: {dir_path}")
print()

# 4. Check data files
print("4. DATA FILES")
if data_dir.exists():
    data_files = list(data_dir.glob("*.parquet")) + list(data_dir.glob("*.xlsx"))
    if data_files:
        for f in sorted(data_files):
            size_kb = f.stat().st_size / 1024
            modified = f.stat().st_mtime
            import datetime
            mod_date = datetime.datetime.fromtimestamp(modified).strftime('%Y-%m-%d %H:%M')
            print(f"   📄 {f.name:25} | {size_kb:8.1f} KB | {mod_date}")
    else:
        print("   ⚠️  No data files found - ETL needs to run")
else:
    print("   ❌ Data directory not found")
print()

# 5. Check ETL scripts
print("5. ETL SCRIPTS")
if etl_dir.exists():
    etl_files = sorted(etl_dir.glob("*etl*.py"))
    if etl_files:
        for f in etl_files:
            if "test" not in f.name and "backup" not in f.name:
                print(f"   📜 {f.name}")
    else:
        print("   ⚠️  No ETL scripts found")
else:
    print("   ❌ ETL directory not found")
print()

# 6. Check API key configuration
print("6. API KEY CONFIGURATION")
import os

# Check environment variable
env_key = os.environ.get('EIA_API_KEY')
if env_key:
    print(f"   ✅ Environment: EIA_API_KEY found ({env_key[:8]}...)")
else:
    print("   ❌ Environment: EIA_API_KEY not set")

# Check secrets.toml
secrets_file = streamlit_dir / "secrets.toml"
if secrets_file.exists():
    print(f"   ✅ Streamlit secrets.toml exists")
    try:
        with open(secrets_file, 'r') as f:
            content = f.read()
            if 'EIA_API_KEY' in content:
                print("   ✅ EIA_API_KEY found in secrets.toml")
            else:
                print("   ⚠️  EIA_API_KEY not found in secrets.toml")
    except Exception as e:
        print(f"   ⚠️  Could not read secrets.toml: {e}")
else:
    print("   ❌ Streamlit secrets.toml NOT FOUND")
    print("      → Need to create .streamlit/secrets.toml")
print()

# 7. Test API connectivity
print("7. API CONNECTIVITY")
try:
    import requests
    response = requests.get("https://api.eia.gov/v2/", timeout=5)
    print(f"   ✅ EIA API reachable (HTTP {response.status_code})")
except Exception as e:
    print(f"   ❌ EIA API not reachable: {e}")
print()

# 8. Test actual API call
print("8. TEST API CALL")
if env_key or secrets_file.exists():
    try:
        import requests
        test_key = env_key
        if not test_key and secrets_file.exists():
            import toml
            secrets = toml.load(secrets_file)
            test_key = secrets.get('EIA_API_KEY')
        
        if test_key:
            url = "https://api.eia.gov/v2/electricity/rto/fuel-type-data/data/"
            params = {
                'api_key': test_key,
                'frequency': 'hourly',
                'data[0]': 'value',
                'facets[respondent][]': 'ERCO',
                'length': 1
            }
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'response' in data and 'data' in data['response']:
                    print(f"   ✅ API call successful - {len(data['response']['data'])} records")
                else:
                    print(f"   ⚠️  API response unexpected format")
            elif response.status_code == 403:
                print(f"   ❌ API key invalid or expired (HTTP 403)")
            else:
                print(f"   ❌ API call failed (HTTP {response.status_code})")
        else:
            print("   ⚠️  No API key found to test")
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
else:
    print("   ⚠️  Skipped - no API key configured")
print()

# 9. Summary and recommendations
print("=" * 60)
print("RECOMMENDATIONS")
print("=" * 60)

issues = []

# Check for missing packages
for pkg in packages:
    try:
        __import__(pkg)
    except ImportError:
        issues.append(f"Install {pkg}: pip install {pkg}")

# Check for secrets
if not secrets_file.exists() and not env_key:
    issues.append("Create .streamlit/secrets.toml with your EIA_API_KEY")

if issues:
    for i, issue in enumerate(issues, 1):
        print(f"{i}. {issue}")
else:
    print("✅ No issues found! ETL should be ready to run.")

print()
print("To run ETL scripts:")
print("  python etl/eia_fuelmix_etl.py")
print("  python etl/eia_plants_etl.py")
print("  python etl/ercot_queue_etl.py")
print("  python etl/price_map_etl.py")
print()
