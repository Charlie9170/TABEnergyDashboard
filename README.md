# Texas Association of Business Energy Dashboard

An automated, real-time visualization dashboard for ERCOT electricity data and Texas energy infrastructure.

![Dashboard](https://img.shields.io/badge/streamlit-live-brightgreen)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Overview

This dashboard provides comprehensive insights into the Texas electricity market through four interactive views:

1. **ERCOT Fuel Mix** - Hourly generation by fuel type with renewable share tracking
2. **Price Map** - Real-time electricity prices across ERCOT nodes
3. **Generation Map** - Existing power generation facilities by fuel type and capacity
4. **Interconnection Queue** - Proposed generation projects in the ERCOT pipeline

Data is automatically updated every 6 hours via GitHub Actions.

## Features

- 🔄 **Auto-updating**: GitHub Actions fetches fresh data every 6 hours
- 📊 **Interactive visualizations**: Built with Plotly and pydeck
- 🎨 **Consistent design**: Fuel-based color coding across all views
- 🌙 **Dark theme**: Professional, easy-on-the-eyes interface
- 📱 **Responsive**: Works on desktop and mobile devices
- ✅ **Data validation**: Automated schema validation ensures data quality

## Tech Stack

- **Frontend**: Streamlit
- **Data Processing**: Python, pandas, pyarrow
- **Visualization**: Plotly (charts), pydeck (maps)
- **Storage**: Parquet files with Snappy compression
- **Automation**: GitHub Actions
- **APIs**: EIA v2 API (fuel mix data)

## Quick Start

### Prerequisites

- Python 3.11 or higher
- EIA API key (free from [EIA](https://www.eia.gov/opendata/))

### Local Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/Charlie9170/TABEnergyDashboard.git
   cd TABEnergyDashboard
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up API key** ⚠️ **CRITICAL SECURITY STEP**
   
   **Never commit API keys to git!** The secrets file is already in `.gitignore`.
   
   Copy the template:
   ```bash
   cp .streamlit/secrets.toml.example .streamlit/secrets.toml
   ```
   
   Edit `.streamlit/secrets.toml` and add your actual key:
   ```toml
   EIA_API_KEY = "your_api_key_here"
   ```
   
   Get your free API key: https://www.eia.gov/opendata/register.php
   
   Alternative - set as environment variable:
   ```bash
   export EIA_API_KEY="your_api_key_here"
   ```

5. **Run ETL scripts to generate data**
   ```bash
   python etl/eia_fuelmix_etl.py
   python etl/price_map_etl.py
   python etl/eia_plants_etl.py
   python etl/interconnection_etl.py
   ```

6. **Start the dashboard** (from repo root)
   ```bash
   streamlit run app/main.py
   ```

7. **Open your browser**
   
   The dashboard will open automatically at `http://localhost:8501`

## Project Structure

```
TABEnergyDashboard/
├── app/                          # Streamlit application
│   ├── main.py                   # Main app entry point
│   ├── tabs/                     # Dashboard tabs
│   │   ├── fuelmix_tab.py        # ERCOT fuel mix view
│   │   ├── price_map_tab.py      # Price map view
│   │   ├── generation_tab.py     # Generation facilities view
│   │   └── queue_tab.py          # Interconnection queue view
│   └── utils/                    # Shared utilities
│       ├── colors.py             # Fuel color palette
│       ├── schema.py             # Data schemas
│       └── loaders.py            # Data loading functions
├── etl/                          # Data extraction scripts
│   ├── eia_fuelmix_etl.py        # EIA fuel mix data (working)
│   ├── price_map_etl.py          # Demo price data
│   ├── eia_plants_etl.py         # Plants stub (TODO)
│   └── interconnection_etl.py    # Queue stub (TODO)
├── data/                         # Data files (gitignored)
│   ├── fuelmix.parquet
│   ├── price_map.parquet
│   ├── generation.parquet
│   └── queue.parquet
├── scripts/                      # Utility scripts
│   └── validate_data.py          # Data validation
├── .streamlit/                   # Streamlit configuration
│   └── config.toml               # Theme and settings
├── .github/workflows/            # GitHub Actions
│   └── etl.yml                   # Automated data updates
├── requirements.txt              # Python dependencies
├── .gitignore                    # Git ignore patterns
└── README.md                     # This file
```

## Data Sources

### Current (Implemented)

- **EIA Fuel Mix**: U.S. Energy Information Administration API v2
  - Endpoint: `electricity/rto/fuel-type-data`
  - Frequency: Hourly
  - Coverage: Last 7 days

- **Price Map**: Demo data (stub for ERCOT real-time prices)

### Planned (Stubs)

- **Generation Map**: EIA Power Plants dataset via ArcGIS FeatureServer
  - URL: https://atlas.eia.gov/datasets/eia::power-plants/

- **Interconnection Queue**: ERCOT public reports or interconnection.fyi
  - URL: https://www.interconnection.fyi/?market=ERCOT

## GitHub Actions Automation

The dashboard uses GitHub Actions to automatically:

1. Fetch fresh data from APIs every 6 hours
2. Run data validation checks
3. Commit and push updated parquet files
4. Trigger on schedule: `0 */6 * * *` (every 6 hours)
5. Allow manual triggering via `workflow_dispatch`

### Setup for Auto-Updates

1. Add `EIA_API_KEY` to repository secrets:
   - Go to repository Settings → Secrets and variables → Actions
   - Add new secret: `EIA_API_KEY` with your API key

2. Ensure Actions have write permissions:
   - Settings → Actions → General → Workflow permissions
   - Select "Read and write permissions"

3. The workflow runs automatically every 6 hours

## Color Palette

Consistent fuel-based color coding across all visualizations:

| Fuel Type | Color | Hex Code |
|-----------|-------|----------|
| Gas | Orange | `#fb923c` |
| Wind | Teal | `#14b8a6` |
| Solar | Yellow | `#eab308` |
| Coal | Gray | `#6b7280` |
| Nuclear | Purple | `#9333ea` |
| Storage | Blue | `#3b82f6` |
| Hydro | Cyan | `#06b6d4` |
| Biomass | Lime | `#84cc16` |

## Development

### Adding a New Tab

1. Create a new file in `app/tabs/` (e.g., `new_tab.py`)
2. Implement a `render()` function
3. Import and add to `app/main.py`
4. Add corresponding ETL script in `etl/`

### Data Schema

All datasets follow canonical schemas defined in `app/utils/schema.py`:

- **Column normalization**: Automatically maps common aliases
- **Type coercion**: Ensures correct data types
- **Validation**: Checks for required columns

Example:
```python
from utils.loaders import load_parquet

df = load_parquet("fuelmix.parquet", "fuelmix")
# Returns validated DataFrame with canonical schema
```

## Troubleshooting

### Data files not found

Run the ETL scripts to generate data:
```bash
python etl/eia_fuelmix_etl.py
python etl/price_map_etl.py
```

### EIA API errors

- Check your API key is correctly set
- Verify API key hasn't exceeded rate limits
- Check EIA API status: https://www.eia.gov/opendata/

### Streamlit not starting

- Run from the repository root: `streamlit run app/main.py`
- Check port 8501 isn't already in use
- Try: `streamlit run app/main.py --server.port 8502`

## Contributing

Contributions welcome! Areas for improvement:

- [ ] Implement real ERCOT price data fetch
- [ ] Implement EIA plants data from FeatureServer
- [ ] Implement interconnection queue data
- [ ] Add historical data trends
- [ ] Add export functionality
- [ ] Add custom date range selection

## Security

### 🔒 API Key Protection

**NEVER commit API keys or secrets to version control!**

This repository is configured to protect your credentials:

✅ `.streamlit/secrets.toml` is in `.gitignore` (never committed)  
✅ Template file provided: `.streamlit/secrets.toml.example`  
✅ Setup instructions require copying template  

**If you accidentally commit a secret:**
1. Immediately regenerate the API key at the provider
2. Remove from git history: `git rm --cached .streamlit/secrets.toml`
3. Update `.gitignore` to prevent future commits
4. Force push: `git push --force` (if already pushed to remote)

### 🔑 API Keys Used

- **EIA API Key**: Free from https://www.eia.gov/opendata/register.php
- **YesEnergy API Key**: (Coming soon) For real-time price data
- **ERCOT API**: Currently using public CDR reports (no key needed)

### 📝 Best Practices

1. Never hardcode credentials in Python files
2. Use environment variables or Streamlit secrets
3. Rotate API keys periodically
4. Use separate keys for dev/staging/production
5. Monitor API usage for suspicious activity

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Data provided by EIA (U.S. Energy Information Administration)
- ERCOT data and market information
- Built with Streamlit, Plotly, and pydeck

## Screenshots

_Screenshots will be added after deployment_

---

**Last Updated**: 2025-10-20  
**Maintainer**: Charlie9170
