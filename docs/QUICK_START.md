# Quick Start Guide

Get the TAB Energy Dashboard running in 5 minutes!

## Prerequisites

- Python 3.11 or higher
- Git
- (Optional) EIA API key for real fuel mix data

## Installation

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/Charlie9170/TABEnergyDashboard.git
cd TABEnergyDashboard

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Generate Demo Data

```bash
# Generate demo data (no API key needed)
python etl/price_map_etl.py
python etl/eia_plants_etl.py
python etl/interconnection_etl.py

# Generate demo fuel mix data
python -c "
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

periods = pd.date_range(end=datetime.now(), periods=168, freq='h', tz='UTC')
fuels = ['GAS', 'WIND', 'SOLAR', 'COAL', 'NUCLEAR']
data = []

for period in periods:
    hour = period.hour
    data.append({'period': period, 'fuel': 'GAS', 'value_mwh': 20000 + 5000 * (0.5 - abs(hour - 12) / 24)})
    data.append({'period': period, 'fuel': 'WIND', 'value_mwh': 8000 + 4000 * (hour / 24)})
    data.append({'period': period, 'fuel': 'SOLAR', 'value_mwh': max(0, 3000 * (1 - abs(hour - 12) / 12))})
    data.append({'period': period, 'fuel': 'COAL', 'value_mwh': 5000})
    data.append({'period': period, 'fuel': 'NUCLEAR', 'value_mwh': 4000})

df = pd.DataFrame(data)
df['last_updated'] = datetime.now().isoformat()
Path('data').mkdir(exist_ok=True)
df.to_parquet('data/fuelmix.parquet', engine='pyarrow', compression='snappy', index=False)
print('✓ Created demo fuelmix.parquet')
"
```

### 3. Run the Dashboard

```bash
cd app
streamlit run main.py
```

The dashboard will open in your browser at `http://localhost:8501`

## Using Real EIA Data (Optional)

### Get an API Key
1. Visit https://www.eia.gov/opendata/
2. Register for a free account
3. Get your API key

### Configure API Key

**Option 1: Environment Variable**
```bash
export EIA_API_KEY="your_api_key_here"
```

**Option 2: Streamlit Secrets**
Create `.streamlit/secrets.toml`:
```toml
EIA_API_KEY = "your_api_key_here"
```

### Run Real ETL
```bash
python etl/eia_fuelmix_etl.py
```

## GitHub Actions Setup

To enable automatic data updates every 6 hours:

1. **Add API Key to Secrets**
   - Go to repository Settings → Secrets and variables → Actions
   - Add new secret: `EIA_API_KEY` with your key

2. **Enable Workflow Permissions**
   - Settings → Actions → General
   - Workflow permissions → "Read and write permissions"
   - Save

3. **Workflow Runs Automatically**
   - Every 6 hours via cron schedule
   - Or manually via Actions tab → ETL Data Updates → Run workflow

## Troubleshooting

### Data files not found
```bash
# Regenerate demo data
python etl/price_map_etl.py
python etl/eia_plants_etl.py
python etl/interconnection_etl.py
```

### Port already in use
```bash
# Use a different port
streamlit run main.py --server.port 8502
```

### Import errors
```bash
# Ensure you're in the app/ directory
cd app
streamlit run main.py
```

### API rate limit
- EIA API has rate limits (check their documentation)
- Demo data works without API calls

## Next Steps

- Read [AUTO_SAVE_GUIDE.md](AUTO_SAVE_GUIDE.md) for data protection
- Check README.md for full documentation
- Implement real data sources for generation and queue tabs
- Deploy to Streamlit Cloud or your platform

## Common Commands

```bash
# Update dependencies
pip install -r requirements.txt --upgrade

# Validate data files
python scripts/validate_data.py

# Run all ETL scripts
python etl/eia_fuelmix_etl.py
python etl/price_map_etl.py
python etl/eia_plants_etl.py
python etl/interconnection_etl.py

# Commit data changes (local dev)
./scripts/auto_commit.sh "Updated data"

# Check Streamlit version
streamlit --version

# Clear Streamlit cache
streamlit cache clear
```

## Support

- Issues: https://github.com/Charlie9170/TABEnergyDashboard/issues
- EIA API Docs: https://www.eia.gov/opendata/documentation/
- Streamlit Docs: https://docs.streamlit.io/

Happy visualizing! 📊⚡
