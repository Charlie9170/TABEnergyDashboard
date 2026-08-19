# Project Context — TAB Energy Dashboard

> **Evidence key:** *(verified: path)* = confirmed from file; *(inferred)* = logical deduction; *(assumption)* = unverified.

---

## Identity

| Attribute | Value | Source |
|-----------|-------|--------|
| **Repository** | `Charlie9170/TABEnergyDashboard` | *(verified: `README.md`)* |
| **Maintainer** | Charlie9170 | *(verified: `README.md` — "Maintainer: Charlie9170")* |
| **Organization** | Texas Association of Business (TAB) | *(verified: `app/main.py` docstring)* |
| **Short description** | Real-time Texas energy market intelligence dashboard for TAB policymakers and member companies | *(verified: `app/main.py` docstring)* |
| **Primary audience** | TAB members, legislators, Texas policymakers | *(verified: `app/tabs/about_tab.py`)* |
| **License** | MIT | *(verified: `README.md`)* |

---

## Mission (verified)

> "An automated, real-time visualization dashboard for ERCOT electricity data and Texas energy infrastructure."
> *(verified: `README.md`)*

The dashboard provides energy market intelligence to help TAB members and policymakers understand the Texas electricity grid.

---

## Core capabilities (verified from code)

1. **ERCOT Fuel Mix** — Hourly generation by fuel type sourced from EIA API  
   *(verified: `app/tabs/fuelmix_tab.py`, `etl/eia_fuelmix_etl.py`)*

2. **Price Map** — Real-time ERCOT Settlement Point Prices fetched from ERCOT public HTML  
   *(verified: `etl/ercot_lmp_etl.py`, `app/tabs/price_map_tab.py`)*

3. **Generation Map** — Texas power plant locations, capacities, and fuel types from EIA API  
   *(verified: `etl/eia_plants_etl.py`, `app/tabs/generation_tab.py`)*

4. **Interconnection Queue** — Active interconnection projects from the monthly ERCOT
   Generator Interconnection Status (GIS) report  
   *(verified: `etl/ercot_gis_queue_etl.py`, `data/queue.parquet` schema)*

5. **Minerals & Critical Minerals** — REE and critical mineral deposits in Texas (manually curated)  
   *(verified: `etl/mineral_etl.py`, `app/tabs/minerals_tab.py`)*

6. **About & Data Sources** — Transparency tab with data source citations  
   *(verified: `app/tabs/about_tab.py`)*

---

## TAB Brand identity (verified from code)

| Token | Value | Source |
|-------|-------|--------|
| Primary color (Navy) | `#1B365D` | *(verified: `app/utils/colors.py`, `app/main.py`)* |
| Accent color (Red) | `#C8102E` | *(verified: `app/utils/colors.py`, `app/main.py`)* |
| Tagline | "Pro Business, Pro Texas" | *(verified: `app/main.py`)* |
| Logo | Loaded from LinkedIn CDN at runtime | *(verified: `app/main.py`)* |

---

## Policy posture (verified from code)

Each data tab renders a short "TAB Policy" statement aligned with TAB's energy policy
positions (reliable diverse grid, competitive markets, streamlined permitting,
interconnection efficiency, critical minerals supply chain). The copy is inline in each
tab module. *(verified: `app/tabs/*.py` — search "TAB Policy")*

A separate `app/utils/advocacy.py` module once held a longer, never-rendered variant of
this copy; it was removed in the Aug 2026 cleanup so only the text users actually see
exists in the tree. Treat the inline copy as authoritative — it appears under TAB's name.

---

## Technology stack (verified)

| Layer | Technology | Version / Note |
|-------|-----------|----------------|
| Frontend | Streamlit | `==1.45.1` *(verified: `requirements.txt`)* |
| Data processing | pandas | pinned *(read `requirements.txt` for the value)* |
| Columnar storage | pyarrow | pinned *(read `requirements.txt` for the value)* |
| Numeric | numpy | pinned *(read `requirements.txt` for the value)* |
| HTTP | requests | `>=2.31.0` *(verified: `requirements.txt`)* |
| HTML parsing | beautifulsoup4, lxml | *(verified: `requirements.txt`)* |
| Charts | plotly | `>=5.17.0` *(verified: `requirements.txt`)* |
| Maps | pydeck | `>=0.8.0` *(verified: `requirements.txt`)* |
| Geospatial | pyshp *(geopandas/shapely/fiona removed — no wheel on the deploy target)* | *(verified: `requirements.txt`)* |
| Excel | openpyxl | *(verified: `requirements.txt`)* |
| CI/CD | GitHub Actions | *(verified: `.github/workflows/etl.yml`)* |
| Deployment | Streamlit Cloud | *(inferred from `.streamlit/config.toml`, `.streamlit_trigger` file)* |
| Python version | 3.11 | *(verified: `.github/workflows/etl.yml`)* |

> **Note on pinned versions:** Core storage dependencies (`streamlit`, `pandas`, `pyarrow`, `numpy`) are pinned to exact versions to ensure parquet schema compatibility between local development and GitHub Actions. *(verified: `requirements.txt` comment)*

---

## Repository age / history signals

- ETL scripts have author dates of 2025-11-10 *(verified: `etl/ercot_lmp_etl.py`)*
- The ERCOT GIS queue pipeline was added Aug 2026 *(verified: `etl/ercot_gis_queue_etl.py`, `.github/workflows/etl.yml`)*
- A set of dated November 2025 status/completion documents was removed in the Aug 2026 documentation cleanup; git history retains them if that period ever needs reconstructing.
