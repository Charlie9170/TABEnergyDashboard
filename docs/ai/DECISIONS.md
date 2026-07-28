# Engineering Decisions — TAB Energy Dashboard

> **Evidence key:** *(verified: path)* = confirmed from file; *(inferred)* = logical deduction; *(assumption)* = unverified.
>
> Each record describes an architectural decision, its rationale, tradeoffs, risks, and confidence level. These records are reconstructed from code analysis; none were written by the original authors unless noted.

---

## DR-001: Parquet as the storage format for all datasets

**Current implementation:** All five datasets are stored as Snappy-compressed Parquet files in `data/`. They are committed to the git repository and read at app startup.  
*(verified: `data/*.parquet`, `etl/*.py`, `app/utils/loaders.py`)*

**Rationale (inferred):** Parquet provides columnar compression for fast analytical reads, is natively supported by pandas/pyarrow, and avoids a database dependency. Committing to git enables Streamlit Cloud to serve data without a separate database or object store.

**Tradeoffs:**
- ✅ Zero infrastructure (no database, no S3, no object store)
- ✅ Fast tab load times (columnar read, ~1 MB files)
- ✅ Git history provides a natural audit trail
- ❌ Not suitable for large datasets (git LFS limit, memory constraints)
- ❌ Each data update requires a git commit; high-frequency updates would bloat git history

**Risks:** If data volume grows significantly (e.g., minute-level fuel mix history), the parquet files will exceed git practical limits. *(inferred)*

**Intentional?** Yes — requirements.txt pins exact versions specifically "to prevent schema mismatch … between local dev and GitHub Actions." *(verified: `requirements.txt` comment)*

**Confidence:** High

---

## DR-002: Exact dependency version pinning for storage layer

**Current implementation:** `streamlit==1.45.1`, `pandas==2.2.3`, `pyarrow==19.0.0`, `numpy==2.1.3` are pinned to exact versions.  
*(verified: `requirements.txt`)*

**Rationale (verified):** Comment in `requirements.txt` states: "PINNED VERSIONS to prevent schema mismatch — These exact versions ensure compatible parquet schema between local dev and GitHub Actions."

**Tradeoffs:**
- ✅ Eliminates silent parquet schema incompatibility across environments
- ❌ Requires manual version bump for security patches
- ❌ May cause dependency conflicts when adding new libraries

**Risks:** Unpinned transitive dependencies may still drift. Security vulnerabilities in pinned versions will not be auto-remediated.

**Intentional?** Yes — explicitly commented. *(verified: `requirements.txt`)*

**Confidence:** High

---

## DR-003: GitHub Actions as ETL scheduler (no external queue/scheduler)

**Current implementation:** `.github/workflows/etl.yml` runs on `schedule: cron: '0 */6 * * *'` — every 6 hours. It installs dependencies, runs ETL scripts, commits parquet files, and pushes to main.  
*(verified: `.github/workflows/etl.yml`)*

**Rationale (inferred):** GitHub Actions is free for public repositories and requires no additional infrastructure. The 6-hour cadence is sufficient for energy market data that changes hourly.

**Tradeoffs:**
- ✅ Zero additional infrastructure or cost
- ✅ ETL logs visible in GitHub Actions UI
- ❌ GitHub Actions cron may have delays under high load
- ❌ ETL failures silently produce stale data (all steps have `continue-on-error: true`)
- ❌ No alerting on ETL failure

**Risks:** Silent ETL failure — all ETL steps use `continue-on-error: true`, so a failing ETL will not fail the workflow but will leave stale data in production. *(verified: `.github/workflows/etl.yml`)*

**Intentional?** The `continue-on-error` pattern appears intentional (to prevent one failed ETL from blocking others), but the lack of failure notification appears unintentional. *(inferred)*

**Confidence:** Medium

---

## DR-004: `.streamlit_trigger` file for Streamlit Cloud redeployment

**Current implementation:** After committing parquet files, the CI writes a UTC timestamp to `.streamlit_trigger` and commits it. This forces Streamlit Cloud to redeploy.  
*(verified: `.github/workflows/etl.yml`)*

**Rationale (inferred):** Streamlit Cloud watches the main branch for any file changes. Updating a lightweight trigger file ensures redeploy even if parquet files are unchanged (binary diff issues with parquet).

**Tradeoffs:**
- ✅ Simple, reliable redeploy mechanism
- ❌ Generates many git commits (one per ETL run every 6 hours ≈ 4 commits/day)

**Intentional?** Yes. *(verified from code comment)*

**Confidence:** High

---

## DR-005: Never use `st.stop()` — graceful degradation

**Current implementation:** `app/utils/loaders.py` explicitly comments "NEVER use st.stop()" and returns empty DataFrames with canonical schemas on error. `app/main.py` uses `safe_render_tab()` to catch per-tab exceptions.  
*(verified: `app/utils/loaders.py`, `app/main.py`)*

**Rationale (inferred):** A single broken ETL or missing data file should not prevent users from accessing other tabs. The policy ensures partial functionality over complete failure.

**Tradeoffs:**
- ✅ Resilient UX — broken tab does not cascade
- ❌ Users may not notice a tab is showing empty/stale data
- ❌ Developer debugging is harder when errors are swallowed

**Intentional?** Yes — explicitly stated in comments. *(verified)*

**Confidence:** High

---

## DR-006: Canonical schema layer (schema.py + loaders.py)

**Current implementation:** `app/utils/schema.py` defines `SCHEMAS` (canonical column names + dtypes) and `COLUMN_ALIASES` (alternative name mappings). `load_parquet()` applies normalization, type coercion, and validation before returning data to tabs.  
*(verified: `app/utils/schema.py`, `app/utils/loaders.py`)*

**Rationale (inferred):** ETL scripts may produce slightly different column names depending on the data source. A centralized schema layer decouples ETL output format from tab consumption.

**Tradeoffs:**
- ✅ Tabs are insulated from ETL column naming changes
- ❌ Schema for `queue` dataset has a known mismatch: canonical uses `fuel`/`proposed_mw` but actual parquet has `fuel_type`/`capacity_mw`. The alias bridge works but creates hidden coupling.

**Risks:** If ETL adds a new required column that is not in `COLUMN_ALIASES`, the tab will silently show empty data.

**Intentional?** Partially — the schema layer appears intentional; the queue mismatch appears to be technical debt. *(inferred)*

**Confidence:** Medium

---

## DR-007: Separate ETL scripts per dataset (not a unified pipeline)

**Current implementation:** Each dataset has its own ETL script in `etl/`. They share no common runner. GitHub Actions calls them sequentially.  
*(verified: `.github/workflows/etl.yml`, `etl/` directory)*

**Rationale (inferred):** Independent scripts allow individual failure isolation and easier debugging. Each script can be run and tested independently.

**Tradeoffs:**
- ✅ Independent execution, isolated failures
- ❌ No shared utilities for retry logic, logging patterns, etc. (some duplication)
- ❌ Order dependency between scripts is implicit (ETL scripts run sequentially in CI)

**Intentional?** Yes. *(inferred from pattern)*

**Confidence:** Medium

---

## DR-008: TAB brand color palette applied globally

**Current implementation:** `app/utils/colors.py` defines `FUEL_COLORS_HEX` using TAB brand colors (Navy `#1B365D`, Red `#C8102E`). A custom Plotly template `tab_theme` is registered at app startup. CSS is applied in three layers.  
*(verified: `app/utils/colors.py`, `app/main.py`)*

**Rationale (inferred):** The dashboard is a branded product for TAB. Visual consistency with TAB's brand identity is a product requirement.

**Tradeoffs:**
- ✅ Consistent brand presentation
- ❌ Color palette is not optimized for data visualization accessibility (Navy/Red contrast against white may be insufficient for some fuel types)
- ❌ Near-white/off-white colors for SOLAR, HYDRO, BIOMASS may be invisible on white backgrounds

**Risks:** Accessibility concerns — very light fuel colors (SOLAR `#E8EAED`, HYDRO `#F0F1F3`, BIOMASS `#F3F4F6`) are near-white and may be invisible in charts. *(verified: `app/utils/colors.py`)*

**Intentional?** The brand alignment is intentional; the accessibility tradeoff may not have been evaluated. *(inferred)*

**Confidence:** High

---

## DR-009: Two parallel ETL workflow files (active + legacy disabled)

**Current implementation:** `.github/workflows/etl.yml` is the active workflow (scheduled + workflow_dispatch). `.github/workflows/etl-old.yml` has the schedule removed and is workflow_dispatch only with a comment "DISABLED: Superseded by etl.yml."  
*(verified: `.github/workflows/etl-old.yml`)*

**Rationale (inferred):** The old workflow was preserved for debugging/reference rather than deleted.

**Tradeoffs:**
- ✅ Preserved debugging reference
- ❌ Confusing — two workflow files in the same directory
- ❌ The old workflow exposes a real API key value in a comment inside `etl.yml.backup` *(verified: `.github/workflows/etl.yml.backup` — see `OPEN_QUESTIONS.md`)*

**Intentional?** Preserving for reference appears intentional; the API key in the backup file is a security risk. *(inferred)*

**Confidence:** Low (rationale is inferred, not stated)*

---

## DR-010: `@st.cache_data(ttl=3600)` for data loading

**Current implementation:** `load_parquet()` is decorated with `@st.cache_data(ttl=3600)`. `get_file_modification_time()` uses `ttl=60`.  
*(verified: `app/utils/loaders.py`)*

**Rationale (inferred):** Prevents repeated parquet disk reads on every Streamlit re-render (which happens on every user interaction). 1-hour TTL matches the ETL cadence (data refreshes every 6 hours anyway).

**Tradeoffs:**
- ✅ Dramatic performance improvement
- ❌ Up to 1-hour delay between ETL refresh and user seeing new data (even after Streamlit redeploy)

**Intentional?** Yes. *(inferred)*

**Confidence:** High
