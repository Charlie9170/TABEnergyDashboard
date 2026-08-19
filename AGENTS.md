# AGENTS.md — AI Agent Instructions for TAB Energy Dashboard

This file provides instructions and context for AI coding agents (GitHub Copilot, Codex, and others) working in this repository.

---

## Read these files first

Before making any change, read the `docs/ai/` documentation in this order:

1. [`docs/ai/README.md`](docs/ai/README.md) — navigation index
2. [`docs/ai/PROJECT_CONTEXT.md`](docs/ai/PROJECT_CONTEXT.md) — what this project is and who uses it
3. [`docs/ai/ARCHITECTURE.md`](docs/ai/ARCHITECTURE.md) — entry point, module structure, Streamlit patterns
4. [`docs/ai/DATA_FLOW.md`](docs/ai/DATA_FLOW.md) — verified ETL → parquet → rendering pipeline
5. [`docs/ai/CURRENT_STATE.md`](docs/ai/CURRENT_STATE.md) — open work and known issues
6. [`docs/ai/OPEN_QUESTIONS.md`](docs/ai/OPEN_QUESTIONS.md) — unresolved ambiguities

---

## Non-negotiable rules

**The rules live in [`CLAUDE.md`](CLAUDE.md) — read its "Rules" section and follow it.**
They are kept in one file on purpose: they previously existed in three places and
drifted out of sync, leaving two copies asserting things that were no longer true.

Two additions that apply to any agent:

1. **Do not modify application behavior** unless explicitly asked. This is a
   production dashboard read by legislators and TAB member companies.
2. **Minimize change scope** — touch only the files the task requires.

---

## Key file locations

| Purpose | Location |
|---------|----------|
| Application entry point | `app/main.py` |
| Tab modules | `app/tabs/<name>_tab.py` |
| Shared utilities | `app/utils/` |
| Data schemas | `app/utils/schema.py` |
| Data loading | `app/utils/loaders.py` |
| Fuel colors | `app/utils/colors.py` |
| ETL scripts | `etl/<name>_etl.py` |
| Parquet data files | `data/*.parquet` |
| CI/CD workflow | `.github/workflows/etl.yml` |
| Streamlit config | `.streamlit/config.toml`, `.streamlit/custom.css` |
| AI documentation | `docs/ai/` |

---

## Known issues and warnings

- `data/minerals_deposits.parquet` is sparse — the minerals tab renders little content.
  It is the only dataset with no automated feed; `etl/mineral_etl.py` is run by hand
  and is not part of CI.
- `etl/texas_counties.py` does not cover every Texas county. Unknown counties fall back
  to the state centroid with a logged warning, so those projects map to the middle of
  Texas rather than their real location.
- Coordinates in `queue.parquet` are county centroids plus deterministic jitter, not
  surveyed sites — the ERCOT GIS report publishes no lat/lon.

---

## Full workflow guardrails

See [`docs/ai/AI_WORKFLOW.md`](docs/ai/AI_WORKFLOW.md) for complete behavioral guidelines.
