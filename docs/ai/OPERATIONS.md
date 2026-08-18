# Operations — TAB Energy Dashboard

> **Evidence key:** *(verified: path)* = confirmed from file; *(inferred)* = logical deduction; *(assumption)* = unverified.

---

## Local development setup

### Prerequisites
- Python 3.11+ *(verified: `.github/workflows/etl.yml`)*
- EIA API key (free from https://www.eia.gov/opendata/register.php) *(verified: `README.md`)*

### Steps

```bash
# 1. Clone
git clone https://github.com/Charlie9170/TABEnergyDashboard.git
cd TABEnergyDashboard

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure API key (NEVER commit this file)
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit .streamlit/secrets.toml and set: EIA_API_KEY = "your_key_here"

# 5. Run ETL scripts to populate data files
python etl/eia_fuelmix_etl.py
python etl/ercot_lmp_etl.py
python etl/eia_plants_etl.py
python etl/ercot_queue_etl.py
python etl/mineral_etl.py

# 6. Start the dashboard (from repo root)
streamlit run app/main.py
# Opens at http://localhost:8501
```
*(verified: `README.md`)*

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
python etl/ercot_queue_etl.py      # Interconnection queue (no API key needed)
python etl/mineral_etl.py          # Minerals (no API key needed)
```

Convenience script to run all:
```bash
bash refresh_all_data.sh
```
*(verified: `refresh_all_data.sh` presence)*

---

## Testing

The repository has limited test coverage. Existing test files:

| File | Purpose |
|------|---------|
| `test_etl_setup.py` | ETL setup/environment tests |
| `test_eia_plants_etl.py` | EIA plants ETL unit tests |
| `test_project.sh` | Shell-based project tests |
| `scripts/validate_data.py` | Data validation script |

Run with:
```bash
python test_etl_setup.py
python test_eia_plants_etl.py
bash test_project.sh
python scripts/validate_data.py
```
*(verified: file presence)*

> **Note:** There are no pytest configuration files or `tests/` directory. Tests appear to be standalone scripts. *(verified: directory listing)*

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
5. `python etl/eia_fuelmix_etl.py` (`continue-on-error: true`, requires `EIA_API_KEY`)
6. `python etl/ercot_lmp_etl.py` (`continue-on-error: true`)
7. `python etl/eia_plants_etl.py` (`continue-on-error: true`, requires `EIA_API_KEY`)
8. `python etl/ercot_queue_etl.py` (`continue-on-error: true`)
9. `python etl/mineral_etl.py` (`continue-on-error: true`)
10. Validate parquet files with inline Python
11. Check for changes: `git diff --exit-code data/`
12. Commit + push if changes exist (skips if no changes)

**Commit message format:**
```
🤖 Auto-update energy data - YYYY-MM-DD HH:MM:SS UTC
```
*(verified: `.github/workflows/etl.yml`)*

### Legacy workflow: `.github/workflows/etl-old.yml`
- **Disabled** — schedule removed; only `workflow_dispatch` trigger
- Kept for debugging reference
- Has more detailed diagnostic output
*(verified: `.github/workflows/etl-old.yml`)*

---

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
| `EIA_API_KEY` | Secret (preferred) or Variable | `etl.yml` | EIA API authentication |

To configure:
1. Go to repository **Settings → Secrets and variables → Actions**
2. Add `EIA_API_KEY` as a repository secret

*(verified: `.github/workflows/etl.yml`, `README.md`)*

### GitHub Actions write permissions
Actions need **Read and write permissions** to commit data files:
- Settings → Actions → General → Workflow permissions → "Read and write permissions"
*(verified: `README.md`)*

---

## Monitoring and alerting

**No monitoring or alerting is configured.** *(verified: no alerting configuration found in workflow files)*

ETL failures are silenced with `continue-on-error: true`. To check ETL health:
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
- `data/*.json` (but `data/mineral_polygons_v2.json` IS committed — it predates this rule or was force-added)

*(verified: `.gitignore`, directory listing)*

---

## Environment variable reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `EIA_API_KEY` | Optional | None (falls back to demo data) | EIA API authentication |
| `DASHBOARD_MODE` | Optional | (not implemented in app code) | Template mentions this; not implemented |

*(verified: `.env.template`, `etl/eia_fuelmix_etl.py`)*
