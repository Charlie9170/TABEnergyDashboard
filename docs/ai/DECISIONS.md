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

**Current implementation:** `streamlit`, `pandas`, `pyarrow`, `numpy` are pinned to exact versions in `requirements.txt`. The pins were raised in Aug 2026 to releases that publish cp314 wheels, because Streamlit Community Cloud moved its build image to Python 3.14 and the older pins had no wheel — the build fell back to compiling pyarrow from source and failed.  
*(verified: `requirements.txt` — read it for the current values rather than trusting a copy here)*

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
- ❌ No alerting on ETL failure
- ❌ The fuel-mix and price-map steps still use `continue-on-error: true`, so those two can fail silently and leave stale data

**Update (Aug 2026):** the blanket `continue-on-error: true` was removed from the
plants and queue ETLs, and two validator scripts now gate the commit step. A bad
parse fails the job before `git add`, so `main` keeps its last-good data instead of
having it overwritten. *(verified: `.github/workflows/etl.yml`)*

**Intentional?** Yes for the two remaining silenced steps; the absence of failure
notification is still unaddressed. *(inferred)*

**Confidence:** High

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

## DR-009: Single ETL workflow file — superseded

**Superseded.** A second, disabled workflow (`etl-old.yml`) was kept alongside
`etl.yml` for debugging reference. It was deleted in `3377292` because it — and a
sibling `etl.yml.backup` — contained a plaintext EIA API key. `.github/workflows/`
now contains only `etl.yml`.

**Outcome:** Do not reintroduce a parallel "legacy" workflow. Git history is the
reference. See `OPEN_QUESTIONS.md` OQ-001 for the credential handling.

*(verified: `.github/workflows/` contains only `etl.yml`, 2026-08-19)*

---

## DR-010: `@st.cache_data(ttl=3600)` for data loading

**Current implementation:** `load_parquet()` is decorated with `@st.cache_data(ttl=3600)`; it is the only cached loader.  
*(verified: `app/utils/loaders.py`)*

**Rationale (inferred):** Prevents repeated parquet disk reads on every Streamlit re-render (which happens on every user interaction). 1-hour TTL matches the ETL cadence (data refreshes every 6 hours anyway).

**Tradeoffs:**
- ✅ Dramatic performance improvement
- ❌ Up to 1-hour delay between ETL refresh and user seeing new data (even after Streamlit redeploy)

**Intentional?** Yes. *(inferred)*

**Confidence:** High

---

## DR-011: Plotly Scattermapbox for the Price Map (superseded an earlier pydeck-only rule)

**Current implementation:** The Price Map renders with Plotly `go.Scattermapbox`; the Generation Map and Queue Map still use pydeck.  
*(verified: `app/tabs/price_map_tab.py` — `import plotly.graph_objects as go`, `go.Scattermapbox`)*

**Rationale:** Shipped as release `v1.1-hub-spoke-plotly` (Nov 2025) for reliable tooltip behavior, which pydeck did not provide on this view.

**History worth knowing:** A November 2025 working-state note carried an explicit rule — *"DO NOT migrate Price Map to Plotly"* (citing mapbox authentication hangs) and *"keep 8 ERCOT zones."* **Both halves were subsequently reversed by shipped work** and the note was deleted as stale. The map is Plotly today and carries all 15 settlement points. Recorded here so the retired prohibition is not reintroduced from memory or from an old branch.

**Tradeoffs:**
- ✅ Working tooltips on the Price Map
- ❌ Two mapping libraries in one app (Plotly here, pydeck elsewhere)

**Intentional?** Yes.

**Confidence:** High *(verified against current code, not inferred)*
