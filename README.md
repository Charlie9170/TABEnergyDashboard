# TAB Energy Dashboard

Automated ERCOT & EIA data visualization dashboard for Texas Association of Business

## Overview

This interactive dashboard provides real-time insights into Texas electricity markets, including:

1. **ERCOT Fuel Mix**: Hourly electricity generation by fuel source from EIA data
2. **ERCOT Price Map**: Geographic distribution of electricity prices across Texas
3. **TX Generation Map**: Major power generation facilities mapped by type and capacity
4. **ERCOT Queue**: Interconnection queue projects and pipeline analysis

## Project Structure

```
TABEnergyDashboard/
├── app/
│   ├── main.py              # Main Streamlit application
│   ├── Tabs/                # Dashboard tab modules
│   │   ├── fuel_mix.py      # ERCOT Fuel Mix tab
│   │   ├── price_map.py     # Price Map tab
│   │   ├── generation_map.py # Generation Map tab
│   │   └── ercot_queue.py   # Queue tab
│   └── utils/               # Shared utilities
│       ├── colors.py        # Color palette
│       └── data_loader.py   # Data loading functions
├── etl/
│   └── fetch_fuel_mix.py    # ETL script for EIA data
├── data/
│   └── ercot_fuel_mix.parquet # Fuel mix data (auto-updated)
├── .streamlit/
│   └── config.toml          # Streamlit dark theme config
├── .github/workflows/
│   └── etl.yml              # Scheduled ETL workflow
└── requirements.txt         # Python dependencies
```

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Charlie9170/TABEnergyDashboard.git
   cd TABEnergyDashboard
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. (Optional) Set up EIA API key for data updates:
   ```bash
   export EIA_API_KEY='your_api_key_here'
   ```
   Get a free API key at: https://www.eia.gov/opendata/register.php

## Running the Dashboard

Start the Streamlit application:

```bash
streamlit run app/main.py
```

The dashboard will open in your browser at http://localhost:8501

## Data Updates

### Automated Updates

The fuel mix data is automatically updated every 6 hours via GitHub Actions workflow.

### Manual Updates

To manually fetch the latest fuel mix data:

```bash
export EIA_API_KEY='your_api_key_here'
python etl/fetch_fuel_mix.py
```

## Features

- **Dark Theme**: Professional dark mode interface optimized for data visualization
- **Interactive Charts**: Plotly-powered interactive charts and graphs
- **Geographic Maps**: Pydeck 3D maps for spatial data visualization
- **Real-time Data**: Automated data updates from EIA API v2
- **Responsive Design**: Works on desktop and tablet devices

## Data Schema

### Fuel Mix Data

| Column | Type | Description |
|--------|------|-------------|
| period | datetime | Timestamp of the data point |
| fuel | string | Fuel type (coal, natural gas, wind, solar, etc.) |
| value_mwh | float | Generation in megawatt-hours |
| last_updated | datetime | When the data was last updated |

## Technologies

- **Streamlit**: Web application framework
- **Plotly**: Interactive charting library
- **Pydeck**: WebGL-powered maps
- **Pandas**: Data manipulation
- **PyArrow**: Parquet file format
- **EIA API v2**: Energy data source

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.

## Contact

Texas Association of Business
