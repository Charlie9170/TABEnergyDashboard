# CLAUDE.md — Context for Claude in TAB Energy Dashboard

This file provides structured context for Claude (and other Anthropic models) working in this repository.

---

## Repository summary

**TAB Energy Dashboard** is a Streamlit web application that provides real-time Texas electricity market intelligence to the Texas Association of Business (TAB) — a pro-business advocacy organization. The dashboard is served on Streamlit Cloud, with data refreshed every 6 hours via GitHub Actions ETL pipelines.

**Repository:** `Charlie9170/TABEnergyDashboard`  
**Entry point:** `app/main.py`  
**Python version:** 3.11  
**Primary framework:** Streamlit 1.45.1

---

## Documentation index

All detailed context lives in `docs/ai/`:

| File | Contains |
|------|---------|
| [`docs/ai/PROJECT_CONTEXT.md`](docs/ai/PROJECT_CONTEXT.md) | Stakeholders, goals, tech stack |
| [`docs/ai/ARCHITECTURE.md`](docs/ai/ARCHITECTURE.md) | Module structure, tab pattern, utilities |
| [`docs/ai/DATA_SOURCES.md`](docs/ai/DATA_SOURCES.md) | External APIs, parquet schemas |
| [`docs/ai/DATA_FLOW.md`](docs/ai/DATA_FLOW.md) | ETL → parquet → Streamlit rendering |
| [`docs/ai/CURRENT_STATE.md`](docs/ai/CURRENT_STATE.md) | TODOs, backup files, data sparsity |
| [`docs/ai/DECISIONS.md`](docs/ai/DECISIONS.md) | 10 architectural decision records |
| [`docs/ai/OPERATIONS.md`](docs/ai/OPERATIONS.md) | Local setup, CI/CD, deployment |
| [`docs/ai/AI_WORKFLOW.md`](docs/ai/AI_WORKFLOW.md) | Guardrails for AI agents |
| [`docs/ai/PROMPT_TEMPLATES.md`](docs/ai/PROMPT_TEMPLATES.md) | Reusable prompts |
| [`docs/ai/OPEN_QUESTIONS.md`](docs/ai/OPEN_QUESTIONS.md) | Unresolved ambiguities |
| [`docs/ai/CHANGELOG_FOR_AI.md`](docs/ai/CHANGELOG_FOR_AI.md) | Architecture-level change log |

---

## Quick architecture reference

```
app/main.py                    ← entry point; configures page, CSS, Plotly theme, tabs
app/tabs/fuelmix_tab.py        ← ERCOT hourly generation by fuel type (EIA API)
app/tabs/price_map_tab.py      ← ERCOT settlement point prices (ERCOT HTML scrape)
app/tabs/generation_tab.py     ← Texas power plants map (EIA API)
app/tabs/queue_tab.py          ← ERCOT interconnection queue (CDR Excel)
app/tabs/minerals_tab.py       ← Texas REE/critical minerals deposits (manual curation)
app/tabs/about_tab.py          ← Data sources and transparency

app/utils/loaders.py           ← load_parquet() with caching and graceful degradation
app/utils/schema.py            ← canonical schemas, column aliases, type coercion
app/utils/colors.py            ← FUEL_COLORS_HEX (TAB brand: Navy #1B365D, Red #C8102E)
app/utils/export.py            ← CSV download buttons
app/utils/advocacy.py          ← TAB policy messages per tab

data/fuelmix.parquet           ← 1384 rows; period, fuel, value_mwh, last_updated
data/price_map.parquet         ← 15 rows; node_id, price_cperkwh, lat, lon, ...
data/generation.parquet        ← 850 rows; plant_name, lat, lon, capacity_mw, fuel, ...
data/queue.parquet             ← 281 rows; project_name, fuel_type, capacity_mw, lat, lon, ...
data/minerals_deposits.parquet ← 1 row (sparse); deposit_name, lat, lon, minerals, ...

etl/eia_fuelmix_etl.py         ← EIA v2 API → fuelmix.parquet (requires EIA_API_KEY)
etl/ercot_lmp_etl.py           ← ERCOT HTML scrape → price_map.parquet
etl/eia_plants_etl.py          ← EIA v2 API → generation.parquet (requires EIA_API_KEY)
etl/ercot_queue_etl.py         ← ERCOT CDR Excel → queue.parquet
etl/mineral_etl.py             ← manual data → minerals_deposits.parquet

.github/workflows/etl.yml      ← runs all ETL every 6h, commits parquets, updates .streamlit_trigger
```

---

## Behavioral rules for Claude

### Do
- Read `docs/ai/` files before acting
- Cite file paths when making factual statements about the codebase
- Distinguish between verified facts and inferences
- Use `load_parquet()` from `app/utils/loaders.py` for all data loading in tabs
- Use `FUEL_COLORS_HEX` from `app/utils/colors.py` for all fuel-type colors
- Update `docs/ai/` files when making structural changes

### Do not
- Call `st.stop()` anywhere in the application
- Hardcode hex colors for fuel types (use `app/utils/colors.py`)
- Add new dependencies without checking for known vulnerabilities
- Change pinned core dependency versions (`streamlit`, `pandas`, `pyarrow`, `numpy`)
- Commit `.streamlit/secrets.toml`
- Make speculative or unprompted changes

---

## Security note

The file `.github/workflows/etl.yml.backup` may contain a leaked EIA API key. See `docs/ai/OPEN_QUESTIONS.md` OQ-001. Do not expose this value in any response.

---

## Evidence conventions

When documenting findings, use these labels:

| Label | Meaning |
|-------|---------|
| *(verified: `path`)* | Confirmed from the cited file |
| *(inferred)* | Logical deduction from verified facts |
| *(assumption)* | Reasonable but unverified |
| *(unknown)* | Cannot be determined |
