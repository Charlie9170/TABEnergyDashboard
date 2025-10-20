# Data Directory

This directory contains data files for the TAB Energy Dashboard.

## Files

- `ercot_fuel_mix.parquet`: ERCOT hourly fuel mix data from EIA API v2
  - Updated automatically via GitHub Actions workflow (every 6 hours)
  - Schema: period (datetime), fuel (str), value_mwh (float), last_updated (datetime)

## Data Sources

- **EIA API v2**: U.S. Energy Information Administration API
  - Endpoint: https://api.eia.gov/v2/electricity/rto/fuel-type-data/data/
  - Region: ERCO (ERCOT)
  - Frequency: Hourly

## Manual Data Updates

To manually fetch and update the fuel mix data:

1. Set your EIA API key (get one free at https://www.eia.gov/opendata/register.php):
   ```bash
   export EIA_API_KEY='your_api_key_here'
   ```

2. Run the ETL script:
   ```bash
   python etl/fetch_fuel_mix.py
   ```

The data will be saved to `ercot_fuel_mix.parquet` in this directory.
