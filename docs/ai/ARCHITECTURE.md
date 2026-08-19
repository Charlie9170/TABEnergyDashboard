# Architecture — TAB Energy Dashboard

> **Evidence key:** *(verified: path)* = confirmed from file; *(inferred)* = logical deduction; *(assumption)* = unverified.

---

## Entry point

```
app/main.py
```
*(verified: `app/main.py` — `st.set_page_config(...)` call, tab rendering)*

The application is run from the repository root with:
```bash
streamlit run app/main.py
```
*(verified: `app/main.py` entry point; data loaders resolve `data/` relative to repo root)*

---

## Top-level repository layout

```
TABEnergyDashboard/
├── app/                        # Streamlit application
│   ├── main.py                 # Entry point (page config, CSS, tab routing)
│   ├── assets/
│   │   ├── README.md
│   │   └── tab_logo.svg
│   ├── tabs/                   # One module per dashboard tab
│   │   ├── __init__.py
│   │   ├── about_tab.py
│   │   ├── fuelmix_tab.py
│   │   ├── generation_tab.py
│   │   ├── minerals_tab.py
│   │   ├── minerals_tab.py.auto_backup    # ← backup artifact
│   │   ├── minerals_tab.py.backup2        # ← backup artifact
│   │   ├── minerals_tab_OLD_BACKUP.py     # ← backup artifact
│   │   ├── price_map_tab.py
│   │   └── queue_tab.py
│   └── utils/                  # Shared utilities
│       ├── __init__.py
│       ├── colors.py           # Fuel type → color mappings
│       ├── data_sources.py     # Data source registry and footer helpers
│       ├── export.py           # CSV download button utility
│       ├── loaders.py          # Cached parquet loading + schema validation
│       ├── schema.py           # Canonical schemas, aliases, type coercion
│       └── table_styling.py    # Pandas Styler configuration
├── data/                       # Parquet files (committed to git)
│   ├── fuelmix.parquet
│   ├── generation.parquet
│   ├── minerals_deposits.parquet
│   ├── price_map.parquet
│   ├── queue.parquet
│   ├── queue_gis_metadata.json # GIS Report provenance + source totals (Task 8)
│   └── ercot_cdr_may2025.xlsx  # Raw ERCOT CDR source — retired, kept for reference (see ercot_queue_etl.py)
├── etl/                        # Data extraction/transform scripts
│   ├── convert_shapefile.py
│   ├── demo_fuelmix_data.py    # Fallback demo data generator
│   ├── eia_fuelmix_etl.py      # EIA fuel mix (production)
│   ├── eia_plants_etl.py       # EIA generation facilities (production)
│   ├── ercot_lmp_etl.py        # ERCOT real-time prices (production)
│   ├── ercot_gis_queue_etl.py  # ERCOT GIS Report queue (production)
│   ├── ercot_queue_etl.py      # ← DEPRECATED (ERCOT CDR queue); archived, imported for its geocoding/write helpers
│   ├── mineral_etl.py          # Minerals (manual only; not in CI)
│   └── texas_counties.py       # County → coordinate lookup for queue ETL
├── scripts/
│   ├── auto_commit.sh
│   ├── download_usgs_minerals.py
│   ├── validate_data.py
│   ├── validate_generation_parquet.py    # CI gate, run after EIA Plants ETL
│   └── validate_gis_queue_parquet.py     # CI gate, run after GIS Queue ETL (Task 8)
├── docs/
│   ├── ai/                     # ← THIS directory
│   ├── MINERALS_DATA_SOURCES.md
│   └── MINERALS_QUICK_START.md
├── tests/
│   ├── test_eia_plants_etl.py
│   └── test_queue_view.py
├── .github/workflows/
│   └── etl.yml                 # The only workflow file
├── .streamlit/
│   ├── config.toml             # Theme (colors, server settings)
│   ├── custom.css              # Extended CSS design system
│   └── secrets.toml.example
├── .env.template
├── .gitignore
├── .streamlit_trigger          # Timestamp file; changes force Streamlit Cloud redeploy
├── refresh_all_data.sh         # Developer convenience script
├── requirements.txt             # Production deps (installed on Streamlit Cloud)
└── requirements-dev.txt         # + pytest, local-only
```
*(verified: directory traversal, 2026-08-19)*

---

## Streamlit application architecture

### Page configuration
`app/main.py` calls `st.set_page_config(...)` once at module level with:
- `layout="wide"`, `initial_sidebar_state="collapsed"`
- Page title: "Texas Association of Business - Energy Dashboard"
*(verified: `app/main.py`)*

### Custom Plotly theme
A custom `tab_theme` Plotly template is registered in `pio.templates` before tab imports. It uses TAB brand colors and Inter font. *(verified: `app/main.py`)*

### CSS loading
Two CSS layers are applied:
1. `app/main.py` calls `load_custom_css()` which reads `.streamlit/custom.css` from disk.
2. An inline `st.markdown('<style>...</style>', unsafe_allow_html=True)` block applies additional overrides.
*(verified: `app/main.py`)*

### Tab routing
Six tabs are created via `st.tabs(...)`. Each tab calls `safe_render_tab(tab_module.render, "Tab Name")`.
*(verified: `app/main.py`)*

```python
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Fuel Mix", "Price Map", "Generation Map",
    "Interconnection Queue", "Minerals & Critical Minerals", "About & Data Sources"
])
```

### Error isolation
`safe_render_tab()` wraps each tab render in a `try/except`. If a tab crashes, it displays an error expander without stopping the other tabs. The codebase explicitly avoids `st.stop()`. *(verified: `app/main.py`, `app/utils/loaders.py`)*

### Session state
`st.session_state.initialized` and `st.session_state.last_tab` are set on first run to prevent unnecessary re-renders. *(verified: `app/main.py`)*

---

## Data loading pipeline (per tab)

Each tab calls `load_parquet(filename, dataset, allow_empty)` from `app/utils/loaders.py`:

```
1. get_data_path(filename)               → absolute path to data/<filename>
2. pd.read_parquet(filepath)             → raw DataFrame
3. normalize_columns(df, dataset)        → rename via COLUMN_ALIASES
4. coerce_types(df, dataset)             → cast columns to canonical dtypes
5. validate(df, dataset)                 → check required columns
6. return df                             → cached for 1 hour (st.cache_data ttl=3600)
```
*(verified: `app/utils/loaders.py`)*

---

## Schema module (`app/utils/schema.py`)

Defines:
- `SCHEMAS` — canonical column names and dtypes for each dataset
- `COLUMN_ALIASES` — maps alternative column names to canonical names
- `normalize_columns()`, `coerce_types()`, `validate()`, `get_schema()`

*(verified: `app/utils/schema.py`)*

See [`DATA_SOURCES.md`](DATA_SOURCES.md) for the full schema table for each dataset.

---

## Styling architecture

| Layer | Location | Scope |
|-------|----------|-------|
| Streamlit theme | `.streamlit/config.toml` | Base colors, font |
| Extended CSS | `.streamlit/custom.css` | Additional component styles |
| Inline CSS | `app/main.py` | Layout overrides (aggressive spacing, nav bar, footer, tab styles) |
| Plotly template | `app/main.py` (registered at startup) | All Plotly charts |
| Table styling | `app/utils/table_styling.py` | Pandas Styler objects |
| Fuel colors | `app/utils/colors.py` | All fuel-type visualizations |

---

## Utilities reference

| Module | Key exports | Purpose |
|--------|-------------|---------|
| `app/utils/loaders.py` | `load_parquet()`, `get_last_updated()`, `get_data_path()` | Cached data loading |
| `app/utils/schema.py` | `SCHEMAS`, `COLUMN_ALIASES`, `normalize_columns()`, `coerce_types()`, `validate()` | Schema contracts |
| `app/utils/colors.py` | `FUEL_COLORS_HEX`, `get_fuel_color_hex()`, `get_fuel_color_rgb()`, `RENEWABLE_FUELS`, `is_renewable()` | Visual consistency |
| `app/utils/data_sources.py` | `DATA_SOURCES`, `render_data_source_footer()`, `render_freshness_banner()` | Source attribution |
| `app/utils/export.py` | `create_download_button()` | CSV export for legislators |
| `app/utils/table_styling.py` | `PROFESSIONAL_TABLE_STYLE`, `apply_professional_table_style()` | Styled DataFrames |

---

## ETL scripts reference

| Script | Status | Data file written | Source |
|--------|--------|------------------|--------|
| `etl/eia_fuelmix_etl.py` | Production | `data/fuelmix.parquet` | EIA v2 API |
| `etl/ercot_lmp_etl.py` | Production | `data/price_map.parquet` | ERCOT public HTML |
| `etl/eia_plants_etl.py` | Production | `data/generation.parquet`, `data/eia860_plant_locations.parquet` | EIA v2 API |
| `etl/ercot_gis_queue_etl.py` | Production | `data/queue.parquet`, `data/queue_gis_metadata.json` | ERCOT GIS Report (monthly) |
| `etl/ercot_queue_etl.py` | **Deprecated** (archived) | — not run | ERCOT CDR Excel — retired, see module docstring |
| `etl/mineral_etl.py` | Manual only (not in CI) | `data/minerals_deposits.parquet` | Manual curation |
| `etl/demo_fuelmix_data.py` | Fallback | `data/fuelmix.parquet` | Synthetic data |
| `etl/convert_shapefile.py` | Utility | N/A | USGS shapefile conversion |
| `etl/texas_counties.py` | Utility | N/A | County → coordinate lookup |

> **Note:** `ercot_queue_etl.py` is deprecated but **must not be deleted** — `ercot_gis_queue_etl.py` imports its geocoding and atomic-write helpers. Extract those first. *(verified: `etl/ercot_gis_queue_etl.py`)*
