# Operations — TAB Energy Dashboard

> **Evidence key:** *(verified: path)* = confirmed from file; *(inferred)* = logical deduction; *(assumption)* = unverified.

---

## Local development setup

### Prerequisites
- Python 3.11–3.13 locally *(verified: local `.venv` runs 3.12.13, 2026-08-19)*
- EIA API key (free from https://www.eia.gov/opendata/register.php) *(verified: `README.md`)*

Three Python versions are in play: local dev on 3.11–3.13, GitHub Actions pinned to
3.11 *(verified: `.github/workflows/etl.yml`)*, and Streamlit Cloud on 3.14, which is
set in the Cloud app's Advanced settings and cannot be pinned from this repo. The
`pandas` / `pyarrow` / `numpy` pins in `requirements.txt` are the releases that
publish cp314 wheels, so the same pins install on all three.

### Steps

```bash
# 1. Clone
git clone https://github.com/Charlie9170/TABEnergyDashboard.git
cd TABEnergyDashboard

# 2. Create virtual environment (name it .venv)
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 3. Install dependencies into that environment (re-run after every pull)
pip install -r requirements.txt

# 4. Configure API key (NEVER commit this file)
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit .streamlit/secrets.toml and set: EIA_API_KEY = "your_key_here"

# 5. Run ETL scripts to populate data files
python etl/eia_fuelmix_etl.py
python etl/ercot_lmp_etl.py
python etl/eia_plants_etl.py
python etl/ercot_gis_queue_etl.py
python etl/mineral_etl.py      # manual only; not run by CI

# 6. Start the dashboard (from repo root)
streamlit run app/main.py
# Opens at http://localhost:8501
```
*(verified: `README.md`)*

### Always install requirements into the venv

If `requirements.txt` is never applied, `pyarrow` stays at whatever version the
environment happened to have, and reading a parquet written by CI with a newer
`pyarrow` fails with `Repetition level histogram size mismatch`. This happened here:
the local `.venv` was created by `uv venv`, which ships no `pip`, so the install was
silently skipped and `pyarrow` sat at 19 while CI wrote with 22. Fix is
`python -m ensurepip --upgrade` followed by `pip install -r requirements.txt`.
*(verified: local environment repair, 2026-08-19)*

### API key alternatives
- Environment variable: `export EIA_API_KEY="your_key_here"` *(verified: `etl/eia_fuelmix_etl.py`)*
- `.env` file (not currently auto-loaded — would require `python-dotenv`) *(assumption — not verified from code)*
- Streamlit secrets file: `.streamlit/secrets.toml` *(verified: `etl/eia_fuelmix_etl.py`)*

---

## Running individual ETL scripts

Each ETL script can be run independently from the repository root:

```bash
python etl/eia_fuelmix_etl.py      # Fuel mix (requires EIA_API_KEY)
python etl/ercot_lmp_etl.py        # Price map (no API key needed)
python etl/eia_plants_etl.py       # Generation map (requires EIA_API_KEY)
python etl/ercot_gis_queue_etl.py  # Interconnection queue (no API key needed)
python etl/mineral_etl.py          # Minerals (manual only; not run by CI)
```

Convenience script to run all:
```bash
bash refresh_all_data.sh
```
*(verified: `refresh_all_data.sh` presence)*

---

## Testing

Real unit tests live in `tests/` and run with pytest. Install dev dependencies first
— `requirements-dev.txt` layers `pytest` on top of `requirements.txt`; it is **not**
installed on Streamlit Cloud, which only ever installs `requirements.txt`:

```bash
pip install -r requirements-dev.txt
python -m pytest tests/
```

| File | Purpose |
|------|---------|
| `tests/test_eia_plants_etl.py` | EIA plants ETL unit tests (25 tests; 3 pre-existing failures as of 2026-08-19, unrelated to this doc pass) |
| `tests/test_queue_view.py` | Queue-view selection contract (committed pipeline vs. full queue) |
| `scripts/validate_data.py` | Data validation script, run directly (not pytest) |

Three former root-level scripts — `test_etl_setup.py`, `test_project.sh`,
`diagnose_etl.py` — were development diagnostics, not tests (no assertions, and
`test_project.sh` asserted things that were no longer true, e.g. a dark theme after
the app switched to light). Deleted in the Aug 2026 cleanup; git history has them.

*(verified: `tests/`, `requirements-dev.txt`, local pytest run, 2026-08-19)*

---

## CI/CD pipeline

### Active workflow: `.github/workflows/etl.yml`

**Trigger:** Cron `0 */6 * * *` (every 6 hours) + `workflow_dispatch` (manual)  
**Permissions:** `contents: write`  
**Runner:** `ubuntu-latest`  
*(verified: `.github/workflows/etl.yml`)*

**Steps:**
1. `actions/checkout@v4` (full history: `fetch-depth: 0`)
2. `actions/setup-python@v5` (Python 3.11, pip cache)
3. `pip install -r requirements.txt`
4. Diagnostic step: checks for `EIA_API_KEY` in secrets and variables
5. `python etl/eia_fuelmix_etl.py` — `continue-on-error: true`, requires `EIA_API_KEY`
6. `python etl/ercot_lmp_etl.py` — `continue-on-error: true`
7. `python etl/eia_plants_etl.py` — **fails the job on error**, requires `EIA_API_KEY`
8. `python etl/ercot_gis_queue_etl.py` — **fails the job on error**
9. `python scripts/validate_generation_parquet.py` — **fails the job on error**
10. `python scripts/validate_gis_queue_parquet.py` — **fails the job on error**
11. Commit `data/*.parquet` + `data/queue_gis_metadata.json`, touch `.streamlit_trigger`, push (skips if no changes)

`etl/mineral_etl.py` is **not** part of this workflow — minerals are curated manually.

The four fail-loud steps are deliberate: a failure stops the job before the commit
step, so `main` keeps its last-good data rather than having it overwritten by a bad
parse. Only the two `continue-on-error: true` steps can fail silently.

**Commit message format:**
```
🤖 Auto-update energy data - YYYY-MM-DD HH:MM:SS UTC
```
*(verified: `.github/workflows/etl.yml`)*

## Deployment

### Platform
Streamlit Cloud *(inferred from `.streamlit/config.toml`, `.streamlit_trigger` mechanism, README badge)*

### How deployment is triggered
1. GitHub Actions ETL run commits changes to `data/*.parquet` and `.streamlit_trigger`
2. Streamlit Cloud detects main branch changes and redeploys automatically
*(verified: `.github/workflows/etl.yml` comment: "Create trigger file to force Streamlit Cloud redeploy")*

### Required repository secrets / variables for CI

| Name | Type | Used by | Purpose |
|------|------|---------|---------|
| `EIA_API_KEY` | **Secret only** | `etl.yml` | EIA API authentication |

To configure:
1. Go to repository **Settings → Secrets and variables → Actions → Secrets**
2. Add `EIA_API_KEY` as a repository **secret**

**Must be a Secret, not a Variable.** The key is a credential, not a
configuration value — it authenticates requests under your registered EIA
identity. GitHub Secrets are masked in Actions logs and never displayed after
creation; Variables are stored and displayed in plaintext. The workflow reads
`secrets.EIA_API_KEY` exclusively, so a Variable of the same name is never
read — creating one only adds confusion.

Verification: re-run the workflow and confirm the fuel mix / plants steps
complete without a 401/403. GitHub redacts the secret value itself in logs, so
you will not see the key echoed.

*(verified: `.github/workflows/etl.yml:38,48` — both use `${{ secrets.EIA_API_KEY }}`; no `vars.` reference exists)*

### GitHub Actions write permissions
Actions need **Read and write permissions** to commit data files:
- Settings → Actions → General → Workflow permissions → "Read and write permissions"
*(verified: `README.md`)*

---

## Monitoring and alerting

**No monitoring or alerting is configured.** *(verified: no alerting configuration found in workflow files)*

The fuel-mix and price-map steps are silenced with `continue-on-error: true`; the
plants and queue ETLs and both validators fail the job. To check ETL health:
- View GitHub Actions run history: `https://github.com/Charlie9170/TABEnergyDashboard/actions`
- Inspect parquet file modification times in the About tab of the dashboard
- Run `python scripts/validate_data.py` locally

---

## Data file management

Parquet files are committed to git and should NOT be in `.gitignore`.  
The `.gitignore` has a commented-out line:
```
# data/*.parquet  # DISABLED - Allow parquet files for automated dashboard updates
```
*(verified: `.gitignore`)*

Raw/interim data formats that ARE gitignored:
- `data/*.csv`
- `data/*.json`, with two explicit negation rules for the sidecars that are
  committed on purpose: `data/queue_gis_metadata.json` (read by the queue validator
  and the About tab) and `data/mineral_polygons_v2.json` (loaded at runtime by the
  minerals tab)

*(verified: `.gitignore`, directory listing)*

---

## Environment variable reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `EIA_API_KEY` | Required by both EIA ETLs | None — the ETL exits 1 and writes nothing | EIA API authentication |
| `DASHBOARD_MODE` | Optional | (not implemented in app code) | Template mentions this; not implemented |

*(verified: `.env.template`, `etl/eia_fuelmix_etl.py`)*
