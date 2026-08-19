# CLAUDE.md — Context for Claude in TAB Energy Dashboard

Streamlit dashboard giving the Texas Association of Business intelligence on the
Texas electricity market. Public-facing: legislators and TAB member companies read it.

**Entry point:** `app/main.py` — run from repo root: `streamlit run app/main.py`
**Pinned:** `streamlit==1.45.1`, `pandas`, `pyarrow`, `numpy` (`requirements.txt`)

## Runtimes differ by environment — do not assume one version

Streamlit Community Cloud (production) runs **Python 3.14**, set in the app's Advanced
settings, not in this repo. GitHub Actions runs 3.11 (`.github/workflows/etl.yml`);
local dev works on 3.11–3.13. The four core pins target releases publishing cp314
wheels, so they cannot drift freely (`docs/ai/OPERATIONS.md`).

## Data flow

ETL scripts write Parquet into `data/`, which is **committed to git**. GitHub Actions
runs them every 6 hours, commits changed data, and touches `.streamlit_trigger` to
force a Cloud redeploy. Tabs read Parquet via `load_parquet()` — never
`pd.read_parquet()` directly.

| ETL | Writes | In CI? |
|---|---|---|
| `eia_fuelmix_etl.py` | `fuelmix.parquet` | yes |
| `ercot_lmp_etl.py` | `price_map.parquet` | yes |
| `eia_plants_etl.py` | `generation.parquet`, `eia860_plant_locations.parquet` | yes |
| `ercot_gis_queue_etl.py` | `queue.parquet`, `queue_gis_metadata.json` | yes |
| `mineral_etl.py` | `minerals_deposits.parquet` | **no — manual only** |

`scripts/validate_generation_parquet.py` and `scripts/validate_gis_queue_parquet.py`
gate the commit step; they fail the job rather than let bad data overwrite good.

Datasets: hourly ERCOT generation by fuel; 15 ERCOT settlement points (the source
maximum); Texas plants with measured EIA-923 generation; the ERCOT GIS
interconnection queue (Large + Small Gen, monthly); a small manually curated minerals
table. Row counts change every refresh — read the Parquet, never trust a doc's count.

## Rules

- Never call `st.stop()` — degrade gracefully (`app/utils/loaders.py`)
- Never show users ETL commands, paths, schemas, or stack traces. Public copy stays
  neutral ("Data temporarily unavailable."); detail goes to `logger.exception`
- Use `load_parquet()` for data loading; `FUEL_COLORS_HEX` for fuel colors
- Don't change the four pins without checking cp314 wheel availability
- Never commit `.streamlit/secrets.toml`; update `docs/ai/` on structural changes

Deeper context: `docs/ai/` (ARCHITECTURE, DATA_SOURCES, DATA_FLOW, DECISIONS,
OPERATIONS, CURRENT_STATE, OPEN_QUESTIONS). Setup lives in `README.md`, nowhere else.
Evidence labels: *(verified: `path`)* · *(inferred)* · *(assumption)*
