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

- Python 3.11–3.13 for local development
- EIA API key (free from [EIA](https://www.eia.gov/opendata/))

GitHub Actions pins Python 3.11; Streamlit Cloud runs Python 3.14 (set in the Cloud
app's Advanced settings, not in this repo). That is why `pandas`, `pyarrow`, and
`numpy` are pinned to releases that publish cp314 wheels.

### Local Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/Charlie9170/TABEnergyDashboard.git
   cd TABEnergyDashboard
   ```

2. **Create a virtual environment** named `.venv`
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies into that environment**
   ```bash
   pip install -r requirements.txt
   ```

   Always run this install, and re-run it after pulling. Skipping it leaves
   `pyarrow` at whatever version the environment already had, and reading a
   CI-written parquet with an older `pyarrow` than the writer fails with
   `Repetition level histogram size mismatch`. If the environment was created by
   `uv venv` it may contain no `pip` at all — run `python -m ensurepip --upgrade`
   first, then install.

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
   python etl/ercot_lmp_etl.py
   python etl/eia_plants_etl.py
   python etl/ercot_gis_queue_etl.py
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
│   │   ├── queue_tab.py          # Interconnection queue view
│   │   ├── minerals_tab.py       # Critical minerals view
│   │   └── about_tab.py          # Data sources / about view
│   └── utils/                    # Shared utilities
│       ├── colors.py             # Fuel color palette
│       ├── schema.py             # Data schemas
│       └── loaders.py            # Data loading functions
├── etl/                          # Data extraction scripts
│   ├── eia_fuelmix_etl.py        # EIA fuel mix data (production)
│   ├── ercot_lmp_etl.py          # ERCOT real-time prices (production)
│   ├── eia_plants_etl.py         # EIA generation facilities (production)
│   ├── ercot_gis_queue_etl.py    # ERCOT GIS interconnection queue (production)
│   └── mineral_etl.py            # Critical minerals (manual, not in CI)
├── data/                         # Data files (committed — refreshed by CI)
│   ├── fuelmix.parquet
│   ├── price_map.parquet
│   ├── generation.parquet
│   ├── queue.parquet
│   └── minerals_deposits.parquet
├── scripts/                      # Utility scripts
│   ├── validate_data.py                  # Data validation
│   ├── validate_generation_parquet.py    # CI gate for generation ETL
│   └── validate_gis_queue_parquet.py     # CI gate for queue ETL
├── .streamlit/                   # Streamlit configuration
│   └── config.toml               # Theme and settings
├── .github/workflows/            # GitHub Actions
│   └── etl.yml                   # Automated data updates
├── requirements.txt              # Python dependencies
├── .gitignore                    # Git ignore patterns
└── README.md                     # This file
```

## Data Sources

Every dashboard view is backed by a live public source. Four ETLs run in CI on the
6-hour schedule; minerals is the one manually curated dataset.

- **ERCOT Fuel Mix** — `etl/eia_fuelmix_etl.py` → `data/fuelmix.parquet`
  - EIA v2 API, endpoint `electricity/rto/fuel-type-data`, respondent `ERCO` (ERCOT)
  - Hourly, trailing 7 days; requires `EIA_API_KEY`

- **Price Map** — `etl/ercot_lmp_etl.py` → `data/price_map.parquet`
  - Scrapes ERCOT's public Real-Time Settlement Point Prices page:
    https://www.ercot.com/content/cdr/html/real_time_spp
  - 15 settlement points (9 hubs/load zones + 6 strategic nodes); no API key needed
  - ERCOT updates roughly every 5 minutes; this dashboard samples it every 6 hours

- **Generation Map** — `etl/eia_plants_etl.py` → `data/generation.parquet`
  - EIA v2 API, endpoints `electricity/operating-generator-capacity` (nameplate
    capacity) and `electricity/facility-fuel` (measured generation), Texas only
  - Plant coordinates come from EIA-860, cached in `data/eia860_plant_locations.parquet`
  - Reported output is a measured three-month average ending on the last complete
    published month. Plants with no measured data are excluded rather than estimated;
    requires `EIA_API_KEY`

- **Interconnection Queue** — `etl/ercot_gis_queue_etl.py` → `data/queue.parquet`
  - ERCOT's monthly Generator Interconnection Status (GIS) Report. The ETL resolves
    the newest `GIS_Report_*` document from ERCOT's public report listing rather than
    a hardcoded URL, then parses the "Project Details - Large Gen" and "Project
    Details - Small Gen" sheets
  - Also writes `data/queue_gis_metadata.json` with the report's own published totals
    and provenance, used as an independent cross-check by the CI validator
  - The GIS report publishes no coordinates, so map positions are county centroids
    with small jitter — accurate to county, not to site; no API key needed

- **Critical Minerals** — `etl/mineral_etl.py` → `data/minerals_deposits.parquet`
  - Manually curated from `data/manual_mineral_deposits.csv`, compiled from public
    geological surveys and industry disclosures, with formation overlays in
    `data/mineral_polygons_v2.json`
  - **Not** run by CI; refreshed only when someone runs the script locally

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
python etl/ercot_lmp_etl.py
python etl/eia_plants_etl.py
python etl/ercot_gis_queue_etl.py
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

Contributions welcome! Live ERCOT prices, EIA plants, the interconnection queue, and
CSV export all shipped — see **Data Sources** above for what each view actually reads.

Open ideas:

- [ ] Historical trends (each parquet is a current snapshot; nothing is retained over time)
- [ ] Custom date range selection (windows are currently fixed per ETL)
- [ ] Broaden `etl/texas_counties.py` coverage so queue projects in unlisted counties
      stop falling back to the state centroid

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
