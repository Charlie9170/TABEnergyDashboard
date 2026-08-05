# Open Questions — TAB Energy Dashboard

> This file tracks unresolved ambiguities about the codebase. When a question is answered, move the answer to the appropriate `docs/ai/` file and remove the entry here.
>
> **Evidence key:** *(verified: path)* = confirmed from file; *(inferred)* = logical deduction; *(assumption)* = unverified.

---

## Security

### OQ-001: ~~Is there a leaked API key in `.github/workflows/etl.yml.backup`?~~ — RESOLVED 2026-07-28

Confirmed: a real EIA API key (`z9d4AvwB...gQyiV`, redacted) was committed in plaintext across 8+ historical commits, in `.github/workflows/etl-old.yml`, `.github/workflows/etl.yml.backup`, and 4 files in `docs/`. `.streamlit/secrets.toml` itself was never committed (confirmed via `git log --all --full-history`).

**Actions taken:**
- Key rotated (new key issued at eia.gov/opendata, provided directly by repo owner, stored only in local `.streamlit/secrets.toml`, never pasted into any tracked file).
- `.github/workflows/etl-old.yml` and `.github/workflows/etl.yml.backup` deleted.
- Old key value scrubbed from `docs/API_KEY_SETUP_GUIDE.md`, `docs/AUTO_UPDATE_FIX_COMPLETE.md`, `docs/ETL_SETUP_COMPLETE.md`, `docs/SECURITY_AUDIT_COMPLETE.md` — replaced with `<your-eia-api-key>` placeholder.
- **Still required (repo owner only, no agent access):** update the `EIA_API_KEY` value in GitHub **Settings → Secrets and variables → Actions**, and in Streamlit Cloud app secrets once deployed.

**Residual risk accepted:** the old key remains visible in git history (not rewritten/purged). Accepted as low-severity — EIA keys are free, rate-limited, read-only, no billing exposure — rotation neutralizes the practical risk without the disruption of a history rewrite (`git filter-repo`).

**Status:** Resolved pending owner's confirmation that the GitHub Actions secret has been updated.

---

## Data pipeline

### OQ-002: Is `etl/price_map_etl.py` still needed?

`etl/price_map_etl.py` is a demo stub that writes hardcoded nodes. `etl/ercot_lmp_etl.py` is the production replacement that writes `data/price_map.parquet`. The CI workflow (`etl.yml`) only calls `ercot_lmp_etl.py`.

**Question:** Should `price_map_etl.py` be deleted to avoid confusion? Or does it serve a development/testing purpose?

**Status:** Unresolved.

---

### OQ-003: Is `etl/interconnection_etl.py` still needed?

`etl/interconnection_etl.py` is an empty stub that only creates an empty queue schema. `etl/ercot_queue_etl.py` is the production replacement. The CI workflow only calls `ercot_queue_etl.py`.

**Question:** Should `interconnection_etl.py` be deleted?

**Status:** Unresolved.

---

### OQ-004: How does `ercot_queue_etl.py` download the latest CDR?

The ETL script comments suggest it attempts to download the latest CDR from ERCOT's website, falling back to `data/ercot_cdr_may2025.xlsx`. 

**Question:** What URL does it use to download the latest CDR? Does this URL reliably point to the current CDR, or does ERCOT change the URL with each release?

**Status:** Unresolved — requires reading the full `ercot_queue_etl.py` download logic.

---

### OQ-005: Why does `minerals_deposits.parquet` have only 1 row?

The parquet file has only 1 row, making the minerals tab effectively empty.

**Question:** Is this expected (placeholder/bootstrap state) or a bug in the ETL? Has the minerals ETL been run with the manually curated data?

**Status:** Unresolved.

---

### OQ-006: Does `etl/eia_plants_etl.py` use the correct EIA endpoint?

The script docstring says "EIA v2 API - Operating Generator Capacity" but the exact endpoint URL was not confirmed in code inspection (the file was too large to read in full).

**Question:** What is the exact EIA v2 endpoint URL used by `eia_plants_etl.py`?

**Status:** Partially unresolved — confirm from `etl/eia_plants_etl.py`.

---

## Architecture

### OQ-007: What is the Streamlit Cloud application URL?

The deployment URL for the live dashboard is not documented in the repository.

**Question:** What is the production URL?

**Status:** Unresolved — not present in any repository file.

---

### OQ-008: Is `data/mineral_polygons_v2.json` used and how?

The file `data/mineral_polygons_v2.json` is committed to the repository but is not listed in the `.gitignore` exclusion for `data/*.json`.

**Question:** Is this file actively used by `app/tabs/minerals_tab.py`? What format does it expect?

**Status:** Unresolved — requires reading `app/tabs/minerals_tab.py` in full.

---

### OQ-009: What does `DASHBOARD_MODE=demo` do?

The `.env.template` mentions:
```
# Optional: Set to 'demo' to use demo data instead of API calls
# DASHBOARD_MODE=demo
```

However, a search of the app code finds no reference to `DASHBOARD_MODE`. 

**Question:** Was this feature implemented and later removed, or was it never implemented?

**Status:** Unresolved — the env var appears in the template but not in app code (based on grep results).

---

### OQ-010: What does `scripts/auto_commit.sh` do?

The file `scripts/auto_commit.sh` exists but was not read in full.

**Question:** Is this script still used? Is it safe to run? Does it overlap with GitHub Actions?

**Status:** Unresolved.

---

## Deployment

### OQ-011: Is `app/assets/tab_logo.svg` used anywhere?

A SVG logo exists at `app/assets/tab_logo.svg` but `app/main.py` loads a logo from a LinkedIn CDN URL at runtime.

**Question:** Was the local SVG replaced by the CDN URL? Should the SVG be used instead (more reliable, works offline)?

**Status:** Unresolved.

---

### OQ-012: What Python version does Streamlit Cloud use?

The CI workflow specifies Python 3.11. Streamlit Cloud may use a different version.

**Question:** Is the Python version on Streamlit Cloud pinned to 3.11, or does it use the platform default?

**Status:** Unresolved — not documented in repository files.
