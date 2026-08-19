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

> **Note:** A demo stub (`etl/price_map_etl.py`) previously wrote hardcoded values to this same path and was deleted in the Aug 2026 cleanup. `ercot_lmp_etl.py` is the only writer of `data/price_map.parquet`. *(verified: `.github/workflows/etl.yml`)*

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

**Source:** ERCOT Generator Interconnection Status (GIS) Report — republished monthly, discovered via ERCOT's public document-listing API (no hardcoded URL)  
**ETL script:** `etl/ercot_gis_queue_etl.py`  
**Output:** `data/queue.parquet`, `data/queue_gis_metadata.json`  
**Dashboard tab:** `app/tabs/queue_tab.py`  
**Validation gate:** `scripts/validate_gis_queue_parquet.py` (runs in CI, no `continue-on-error`, before commit)

### ETL steps (high-level — full details in `etl/ercot_gis_queue_etl.py`)
1. Queries `https://www.ercot.com/misapp/servlets/IceDocListJsonWS?reportTypeId=15933`, filters to `FriendlyName` starting `GIS_Report_`, takes the newest `PublishDate`, downloads by `DocID`
2. Parses `Project Details - Large Gen` and `Project Details - Small Gen` sheets (header row discovered by scanning for `INR` in column 0, not hardcoded skiprows)
3. Maps coded `Fuel`/`Technology` to friendly names via the report's own Acronyms legend, with `(Fuel=OTH, Technology=BA) → "Battery Storage"` handled before the generic map
4. Derives a 3-bucket `status` enum ("Early Stage" / "Under Study" / "Interconnection Agreement Signed") from the free-text `GIM Study Phase` column
5. Calls `texas_counties.get_county_coordinates_for_project()` (reused from the retired `ercot_queue_etl.py`) to geocode county → (lat, lon) + jitter — the GIS report has no coordinates of its own
6. Writes the full unfiltered union of both sheets to `data/queue.parquet`; the tab defaults to **signed interconnection agreement** (SGIA/IA milestone, not a 75 MW cut — that threshold is SB6 large-*load* policy). Full public-sheet view is a render-time toggle. Headline counts use the selected view's complete rows; the map may show a mappable subset.
7. Writes `data/queue_gis_metadata.json` with the source report's own published totals (project count, capacity under study), used by the validation gate as an independent cross-check

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
