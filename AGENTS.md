# AGENTS.md — AI Agent Instructions for TAB Energy Dashboard

This file provides instructions and context for AI coding agents (GitHub Copilot, Codex, and others) working in this repository.

---

## Read these files first

Before making any change, read the `docs/ai/` documentation in this order:

1. [`docs/ai/README.md`](docs/ai/README.md) — navigation index
2. [`docs/ai/PROJECT_CONTEXT.md`](docs/ai/PROJECT_CONTEXT.md) — what this project is and who uses it
3. [`docs/ai/ARCHITECTURE.md`](docs/ai/ARCHITECTURE.md) — entry point, module structure, Streamlit patterns
4. [`docs/ai/DATA_FLOW.md`](docs/ai/DATA_FLOW.md) — verified ETL → parquet → rendering pipeline
5. [`docs/ai/CURRENT_STATE.md`](docs/ai/CURRENT_STATE.md) — active TODOs, backup files, known issues
6. [`docs/ai/OPEN_QUESTIONS.md`](docs/ai/OPEN_QUESTIONS.md) — unresolved ambiguities

---

## Non-negotiable rules

1. **Do not modify application behavior** unless explicitly asked to do so. This is a production dashboard.
2. **Do not commit secrets or API keys** — the `.streamlit/secrets.toml` file must stay in `.gitignore`.
3. **Do not call `st.stop()`** — use graceful degradation (see `app/utils/loaders.py`).
4. **Do not change pinned dependency versions** (`streamlit`, `pandas`, `pyarrow`, `numpy`) without understanding parquet schema compatibility implications.
5. **Minimize change scope** — touch only the files required by the task.
6. **Update `docs/ai/` files** when making structural changes (new tab, schema change, new ETL).

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

- `data/minerals_deposits.parquet` has only 1 row — the minerals tab is nearly empty.
- `.github/workflows/etl.yml.backup` may contain a leaked API key — see `docs/ai/OPEN_QUESTIONS.md` OQ-001.
- The `README.md` project structure is outdated — trust `docs/ai/ARCHITECTURE.md` instead.
- Multiple `.backup` files exist in `app/tabs/` and `etl/` — they are not active code.

---

## Full workflow guardrails

See [`docs/ai/AI_WORKFLOW.md`](docs/ai/AI_WORKFLOW.md) for complete behavioral guidelines.

## Reusable prompts

See [`docs/ai/PROMPT_TEMPLATES.md`](docs/ai/PROMPT_TEMPLATES.md) for prompts covering orientation, bug diagnosis, implementation planning, and more.

---

## Cursor Cloud specific instructions

- Dependencies are installed into a project-local virtualenv at `.venv` (gitignored). The startup update script runs `python3 -m venv .venv` + `pip install -r requirements.txt`. Always invoke tools through that venv, e.g. `.venv/bin/streamlit`, `.venv/bin/python`.
- Run the app (dev mode): `.venv/bin/streamlit run app/main.py --server.port 8501 --server.headless true`. It serves on port `8501` (`/_stcore/health` returns 200 when ready).
- The Streamlit app only **reads** the committed `data/*.parquet` files and gracefully degrades if any are missing — it needs **no API key, no database, and no ETL run** to boot and render all tabs. Do not require `EIA_API_KEY` just to run/view the dashboard.
- `EIA_API_KEY` is only used by the ETL scripts (`etl/eia_*.py`, `refresh_all_data.sh`) that regenerate parquet data. It is optional for development.
- The root-level `test_*.py` files (`test_etl_setup.py`, `test_eia_plants_etl.py`) are ETL smoke tests that make **live EIA API calls and require a valid `EIA_API_KEY`**; they are not part of the app's runnable test suite and will fail without the key. There is no configured linter (no flake8/ruff/pyproject config) and no offline unit-test suite.
- Quick offline health check for the data layer: `.venv/bin/python scripts/validate_data.py` (validates all parquet schemas). A harmless `terminate called without an active exception` may print at exit — the script still exits 0.
- Note (Python 3.12): the deployment target pins Python 3.11, but the pinned deps install and run cleanly on the VM's Python 3.12. Creating the venv requires the system `python3.12-venv` package (already present in the environment snapshot).
