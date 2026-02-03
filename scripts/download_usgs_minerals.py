"""
Download and process USGS mineral deposit data for Texas.

Alternative sources if MRDS shapefile download fails:
1. USGS Mineral Deposit Database (MDD) - JSON API
2. Texas Bureau of Economic Geology data portal
3. Pre-processed Texas mineral data from data.gov
"""

import requests
import json
from pathlib import Path

def download_texas_minerals():
    """
    Download Texas mineral deposit data from USGS API.
    
    This uses the USGS Mineral Deposit Database API which provides
    point locations and attributes for mineral deposits.
    """
    # USGS Mineral Deposit Database API endpoint
    # This is more reliable than downloading the full shapefile
    api_url = "https://mrdata.usgs.gov/services/mdd"
    
    # Query for Texas mineral deposits
    params = {
        'f': 'json',
        'where': "state='TX'",
        'outFields': '*',
        'returnGeometry': 'true'
    }
    
    print("🔍 Querying USGS Mineral Deposit Database for Texas...")
    print(f"   API: {api_url}")
    
    try:
        response = requests.get(f"{api_url}/query", params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        if 'features' in data:
            print(f"✅ Found {len(data['features'])} mineral deposits in Texas")
            
            # Save raw API response
            output_path = Path(__file__).parent.parent / "data" / "temp" / "usgs_texas_minerals_raw.json"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"💾 Saved to: {output_path}")
            return data
        else:
            print("❌ No features found in API response")
            return None
            
    except requests.exceptions.Timeout:
        print("⏱️  API request timed out")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    download_texas_minerals()
