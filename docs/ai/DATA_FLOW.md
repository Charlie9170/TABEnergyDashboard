# Data Flow — TAB Energy Dashboard

> **Evidence key:** *(verified: path)* = confirmed from file; *(inferred)* = logical deduction; *(assumption)* = unverified.
>
> This document traces the verified, end-to-end path data takes from external source to rendered UI. Do not assume any flow is correct without checking the cited files.

---

## Pipeline overview

```
External Source (API / HTML / Excel)
         │
         ▼
    ETL Script (etl/*.py)
         │  extracts, transforms, validates
         ▼
  data/*.parquet  ──── committed to git main branch
         │
         ▼
  GitHub Actions (push triggers Streamlit Cloud redeploy
                  via .streamlit_trigger timestamp change)
         │
         ▼
  Streamlit Cloud reads latest main branch
         │
         ▼
  load_parquet() in app/utils/loaders.py
     ├─ normalize_columns()
     ├─ coerce_types()
     └─ validate()
         │  @st.cache_data(ttl=3600)
         ▼
  Tab render() function  ──  charts (Plotly) + maps (pydeck) + tables
```

---

## Step-by-step: Fuel Mix

**Source:** EIA v2 API → `electricity/rto/fuel-type-data/data/` with `facets[respondent][]=ERCO`  
**ETL script:** `etl/eia_fuelmix_etl.py`  
**Output:** `data/fuelmix.parquet`  
**Dashboard tab:** `app/tabs/fuelmix_tab.py`

### ETL steps (verified: `etl/eia_fuelmix_etl.py`)
1. `get_api_key()` — reads `EIA_API_KEY` from env → Streamlit secrets → demo fallback
2. `fetch_eia_data(api_key, start_date, end_date)` — paginated GET requests (5000 rows/page), last 7 days, sorted by `period` ascending
3. `transform_data(df)`:
   - Select `['period', 'type-name', 'value']` → rename to `['period', 'fuel', 'value_mwh']`
   - Convert `period` to UTC datetime
   - Coerce `value_mwh` to numeric; drop nulls
   - Uppercase `fuel` names
   - Add `last_updated` (UTC ISO string)
   - Sort by `['period', 'fuel']`
4. Write to `data/fuelmix.parquet` with snappy compression via pyarrow

### Loading steps (verified: `app/utils/loaders.py`, `app/utils/schema.py`)
1. `load_parquet("fuelmix.parquet", "fuelmix", allow_empty=True)`
2. `normalize_columns(df, "fuelmix")` — renames `type` → `fuel`, `value` → `value_mwh`, etc.
3. `coerce_types(df, "fuelmix")` — ensures `period` is `datetime64[ns, UTC]`, `value_mwh` is `float64`
4. `validate(df, "fuelmix")` — checks for `['period', 'fuel', 'value_mwh', 'last_updated']`
5. Returns cached DataFrame (1-hour TTL)

---

## Step-by-step: Price Map

**Source:** ERCOT public HTML — `https://www.ercot.com/content/cdr/html/real_time_spp`  
**ETL script:** `etl/ercot_lmp_etl.py`  
**Output:** `data/price_map.parquet`  
**Dashboard tab:** `app/tabs/price_map_tab.py`

### ETL steps (verified: `etl/ercot_lmp_etl.py`)
1. HTTP GET to ERCOT public HTML endpoint (no auth required)
2. BeautifulSoup parses HTML table (class `tableStyle`)
3. Maps settlement point column headers to `ERCOT_ZONES` dict (15 zones with lat/lon/tier)
4. Calculates `avg_price` per zone; assembles DataFrame with `node_id`, `lat`, `lon`, `price_cperkwh`, `region`, `tier`, `last_updated`, `zone_key`, `avg_price`, `interval_end`, `oper_day`
5. Writes to `data/price_map.parquet`

> **Note:** `etl/price_map_etl.py` is a **demo stub** that writes hardcoded data. The CI workflow runs `ercot_lmp_etl.py` (production), not `price_map_etl.py`. *(verified: `.github/workflows/etl.yml`)*

---

## Step-by-step: Generation Map

**Source:** EIA v2 API (Operating Generator Capacity endpoint for Texas plants ≥1 MW)  
**ETL script:** `etl/eia_plants_etl.py`  
**Output:** `data/generation.parquet`  
**Dashboard tab:** `app/tabs/generation_tab.py`

### ETL steps (high-level — full details in `etl/eia_plants_etl.py`)
1. Reads `EIA_API_KEY` from env or Streamlit secrets
2. Fetches Texas power plant data from EIA API (Operating Generator Capacity)
3. Geocodes plants to lat/lon coordinates
4. Writes canonical schema + `actual_generation_mw` column to `data/generation.parquet`

---

## Step-by-step: Interconnection Queue

**Source:** ERCOT CDR Excel report — file `data/ercot_cdr_may2025.xlsx` (committed)  
**ETL script:** `etl/ercot_queue_etl.py`  
**Output:** `data/queue.parquet`  
**Dashboard tab:** `app/tabs/queue_tab.py`

### ETL steps (high-level — full details in `etl/ercot_queue_etl.py`)
1. Attempts to download the latest CDR from ERCOT's website; falls back to `data/ercot_cdr_may2025.xlsx`
2. Parses Excel sheet for planned/future generation projects
3. Extracts project name, fuel type, technology, status, county, capacity, expected date
4. Calls `texas_counties.py` to geocode county → (lat, lon)
5. Validates Texas coordinate bounds (lat 25.8–36.5, lon -106.7 to -93.5)
6. Writes to `data/queue.parquet` (281 rows in current file)

---

## Step-by-step: Minerals

**Source:** Manual curation from GLO, USGS, industry announcements  
**ETL script:** `etl/mineral_etl.py`  
**Output:** `data/minerals_deposits.parquet`, `data/mineral_polygons_v2.json`  
**Dashboard tab:** `app/tabs/minerals_tab.py`

### ETL steps (high-level — full details in `etl/mineral_etl.py`)
1. Loads manually curated CSV or GeoJSON data
2. Validates coordinates within Texas bounds (`TEXAS_BOUNDS` dict)
3. Classifies deposits by development status (Major, Early, Exploratory, Discovery)
4. Optionally generates polygon overlays from USGS MRDS shapefile (skipped if shapefile absent)
5. Writes to `data/minerals_deposits.parquet` (currently 1 row — very sparse data)

---

## GitHub Actions → Streamlit Cloud redeploy mechanism

The CI workflow commits changes to `data/*.parquet` and then updates `.streamlit_trigger`:

```bash
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > .streamlit_trigger
git add .streamlit_trigger
```
*(verified: `.github/workflows/etl.yml`)*

Streamlit Cloud watches the main branch. When `.streamlit_trigger` changes, it triggers a redeploy that loads the new parquet files. *(inferred from code comment "Create trigger file to force Streamlit Cloud redeploy")*

---

## Caching behavior

| Cache | Location | TTL | Scope |
|-------|----------|-----|-------|
| `load_parquet()` | `app/utils/loaders.py` | 3600 seconds (1 hour) | Per parquet file + dataset |
| `get_file_modification_time()` | `app/utils/loaders.py` | 60 seconds | Per filename |

*(verified: `app/utils/loaders.py`)*

> **Implication for freshness:** Even after a GitHub Actions ETL run updates parquet files and triggers a Streamlit Cloud redeploy, the in-memory Streamlit cache may serve stale data for up to 1 hour per tab. This is by design for performance.

---

## Error handling in data flow

If a parquet file is missing, empty, corrupt, or has schema mismatches:
- `load_parquet()` returns an empty DataFrame with the canonical column names
- The tab renders a warning + instructions to run the ETL script
- Other tabs remain unaffected
- `st.stop()` is **never called**

*(verified: `app/utils/loaders.py`)*

---

## Schematic (per-dataset)

```
EIA API / ERCOT HTML / Excel file
     │
     │  etl/*.py  (GitHub Actions, every 6h)
     ▼
data/*.parquet  (committed to git main)
     │
     │  .streamlit_trigger updated
     ▼
Streamlit Cloud redeploy
     │
     │  app/utils/loaders.load_parquet()
     │  └─ normalize → coerce → validate
     │  └─ @st.cache_data(ttl=3600)
     ▼
tab.render()
     ├─ Plotly figures  (fuelmix_tab, price_map_tab)
     ├─ pydeck maps     (generation_tab, queue_tab, minerals_tab)
     └─ st.dataframe    (queue_tab, about_tab)
```
