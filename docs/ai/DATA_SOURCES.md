# Data Sources — TAB Energy Dashboard

> **Evidence key:** *(verified: path)* = confirmed from file; *(inferred)* = logical deduction; *(assumption)* = unverified.

---

## Overview

| Dataset | Parquet file | Source | Update cadence | Status |
|---------|-------------|--------|----------------|--------|
| Fuel Mix | `data/fuelmix.parquet` | EIA v2 API (`electricity/rto/fuel-type-data`, respondent ERCO) | Every 6 hours via GitHub Actions | Production |
| Price Map | `data/price_map.parquet` | ERCOT public HTML (`real_time_spp`) | Every 6 hours via GitHub Actions | Production |
| Generation | `data/generation.parquet` | EIA v2 API (Operating Generator Capacity) | Every 6 hours via GitHub Actions | Production |
| Queue | `data/queue.parquet` | ERCOT CDR Excel report (local file) | Every 6 hours via GitHub Actions | Production |
| Minerals | `data/minerals_deposits.parquet` | Manual curation (GLO, USGS, industry) | Manual / on-demand | Production (sparse) |

*(verified: `app/utils/data_sources.py`, `.github/workflows/etl.yml`)*

---

## EIA API (Fuel Mix and Generation)

- **Base URL:** `https://api.eia.gov/v2`
- **Fuel mix endpoint:** `electricity/rto/fuel-type-data/data/`
- **Generation endpoint:** EIA Operating Generator Capacity (exact endpoint in `etl/eia_plants_etl.py`)
- **Auth:** `EIA_API_KEY` — set as GitHub Actions repository secret `secrets.EIA_API_KEY` or variable `vars.EIA_API_KEY`
- **ERCOT respondent code:** `ERCO`
- **Fallback:** If `EIA_API_KEY` is not set, `eia_fuelmix_etl.py` calls `demo_fuelmix_data.py` to generate synthetic data
*(verified: `etl/eia_fuelmix_etl.py`, `.github/workflows/etl.yml`)*

### API key resolution order (fuel mix ETL)
1. Environment variable `EIA_API_KEY`
2. Streamlit secrets (`st.secrets.get('EIA_API_KEY')`)
3. Fall back to demo data generation

*(verified: `etl/eia_fuelmix_etl.py` — `get_api_key()`)*

### API key resolution order (CI workflow)
The workflow exports `EIA_API_KEY` as: `${EIA_API_KEY_SECRET:-$EIA_API_KEY_VAR}` (secret takes precedence over variable).
*(verified: `.github/workflows/etl.yml`)*

---

## ERCOT Real-Time Settlement Point Prices

- **URL:** `https://www.ercot.com/content/cdr/html/real_time_spp`
- **Format:** HTML page with a table (class `tableStyle`)
- **No API key required** (public)
- **Coverage:** 15 settlement points — 9 major hubs + 6 strategic nodes *(verified: `etl/ercot_lmp_etl.py`)*
- **Update frequency at source:** Every 5 minutes *(verified: `etl/ercot_lmp_etl.py` comment)*
- **ETL scrape frequency:** Every 6 hours via GitHub Actions *(verified: `.github/workflows/etl.yml`)*

### ERCOT settlement points (verified)

| Key | Label | Tier |
|-----|-------|------|
| HB_NORTH | North (Dallas) | hub |
| HB_HOUSTON | Houston | hub |
| HB_SOUTH | South (Corpus/Laredo) | hub |
| HB_WEST | West (Odessa/Midland) | hub |
| LZ_SOUTH | South Central (Austin) | hub |
| LZ_NORTH | East (Tyler/Longview) | hub |
| HB_PAN | Panhandle (Amarillo) | hub |
| HB_BUSAVG | Grid Average | hub |
| HB_HUBAVG | Hub Average | hub |
| LZ_HOUSTON | Houston Central | strategic |
| LZ_WEST | Midland | strategic |
| LZ_CPS | San Antonio (CPS Energy) | strategic |
| LZ_LCRA | Austin Area (LCRA) | strategic |
| LZ_AEN | Northeast Texas (AEP) | strategic |
| LZ_RAYBN | East Texas (Rayburn) | strategic |

*(verified: `etl/ercot_lmp_etl.py` — `ERCOT_ZONES` dict)*

---

## ERCOT CDR (Interconnection Queue)

- **Source file:** `data/ercot_cdr_may2025.xlsx` (committed to repository)
- **Description:** ERCOT Capacity, Demand and Reserves (CDR) Report — May 2025 revision
- **ETL script:** `etl/ercot_queue_etl.py`
- **No API key required** (public Excel report)
- **Note:** The ETL also attempts to download the latest CDR from ERCOT's website; the committed `.xlsx` file serves as a fallback
*(verified: `data/ercot_cdr_may2025.xlsx` presence, `app/utils/data_sources.py`)*

---

## Minerals Data

- **Sources cited in code:** Texas General Land Office (GLO), USGS, industry announcements
- **ETL script:** `etl/mineral_etl.py`
- **Geospatial polygons:** `data/mineral_polygons_v2.json` (committed)
- **Polygon generation:** Requires USGS MRDS shapefile (`~/Downloads/Texas Lithium Shapefile/mrds-trim.shp`); ETL gracefully skips polygon generation if the shapefile is absent *(verified: `.github/workflows/etl.yml` comment, `etl/mineral_etl.py`)*
- **Current data volume:** 1 row in `data/minerals_deposits.parquet` *(verified: parquet inspection)*
- **Update method:** Manual — no automated API; data added by editing ETL or CSV inputs

---

## Parquet schemas (verified from actual files)

### `data/fuelmix.parquet`
| Column | Dtype | Description |
|--------|-------|-------------|
| `period` | `datetime64[ns, UTC]` | Hourly timestamp (UTC) |
| `fuel` | `StringDtype` | Fuel type (uppercase, e.g. "GAS", "WIND") |
| `value_mwh` | `int64` | Generation in MWh |
| `last_updated` | `StringDtype` | ISO timestamp of ETL run |

Current shape: (1384, 4) *(verified: parquet inspection)*

### `data/price_map.parquet`
| Column | Dtype | Description |
|--------|-------|-------------|
| `node_id` | `StringDtype` | Settlement point key (e.g. "HB_NORTH") |
| `region` | `StringDtype` | Human-readable region name |
| `price_cperkwh` | `float64` | Price in cents per kWh |
| `lat` | `float64` | Latitude |
| `lon` | `float64` | Longitude |
| `tier` | `StringDtype` | "hub" or "strategic" |
| `last_updated` | `StringDtype` | ISO timestamp |
| `zone_key` | `StringDtype` | ERCOT zone key |
| `avg_price` | `float64` | Average price |
| `interval_end` | `StringDtype` | Interval end time |
| `oper_day` | `StringDtype` | Operating day |

Current shape: (15, 11) *(verified: parquet inspection)*

> **Note:** The canonical schema in `app/utils/schema.py` defines fewer columns (`node_id`, `lat`, `lon`, `price_cperkwh`, `region`, `last_updated`). The actual parquet file has additional columns written by `ercot_lmp_etl.py`. The schema validator treats extra columns as non-fatal. *(verified: `app/utils/loaders.py` — extra columns are silently ignored)*

### `data/generation.parquet`
| Column | Dtype | Description |
|--------|-------|-------------|
| `plant_name` | `StringDtype` | Power plant name |
| `lat` | `float64` | Latitude |
| `lon` | `float64` | Longitude |
| `capacity_mw` | `float64` | Nameplate capacity in MW |
| `fuel` | `StringDtype` | Fuel type |
| `last_updated` | `StringDtype` | ISO timestamp |
| `actual_generation_mw` | `float64` | Actual generation (extra col, not in canonical schema) |

Current shape: (850, 7) *(verified: parquet inspection)*

### `data/queue.parquet`
| Column | Dtype | Description |
|--------|-------|-------------|
| `project_name` | `StringDtype` | Project name |
| `fuel_type` | `StringDtype` | Fuel/technology type |
| `technology` | `StringDtype` | Technology description |
| `status` | `StringDtype` | Interconnection status |
| `county` | `StringDtype` | Texas county |
| `capacity_mw` | `float64` | Proposed capacity in MW |
| `expected_date` | `StringDtype` | Expected online date |
| `lat` | `float64` | Latitude |
| `lon` | `float64` | Longitude |
| `data_source` | `StringDtype` | Source citation |
| `last_updated` | `StringDtype` | ISO timestamp |

Current shape: (281, 11) *(verified: parquet inspection)*

> **Note:** The canonical schema in `app/utils/schema.py` uses `fuel` (not `fuel_type`) and `proposed_mw` (not `capacity_mw`). Column aliases in `COLUMN_ALIASES["queue"]` map between them. *(verified: `app/utils/schema.py`)*

### `data/minerals_deposits.parquet`
| Column | Dtype | Description |
|--------|-------|-------------|
| `deposit_name` | `StringDtype` | Deposit name |
| `lat` | `float64` | Latitude |
| `lon` | `float64` | Longitude |
| `minerals` | `StringDtype` | Comma-separated mineral list |
| `estimated_tonnage` | `int64` | Estimated tonnage |
| `development_status` | `StringDtype` | Status (Major, Early, Exploratory, Discovery) |
| `county` | `StringDtype` | Texas county |
| `details` | `StringDtype` | Description text |
| `color` | `object` | Visualization color |
| `radius` | `int64` | Map marker radius |
| `tooltip` | `StringDtype` | Map tooltip text |
| `data_source` | `StringDtype` | Source citation |
| `last_updated` | `StringDtype` | ISO timestamp |

Current shape: (1, 13) — **very sparse** *(verified: parquet inspection)*

---

## Credentials and secrets

| Credential | Usage | How to set |
|-----------|-------|-----------|
| `EIA_API_KEY` | EIA fuel mix + generation ETL | GitHub Actions secret `EIA_API_KEY`; locally via `.streamlit/secrets.toml` or env var |

No other API keys are currently required. *(verified: `.github/workflows/etl.yml`, `.streamlit/secrets.toml.example`)*

The `.streamlit/secrets.toml` file is in `.gitignore` and must never be committed. *(verified: `.gitignore`)*
