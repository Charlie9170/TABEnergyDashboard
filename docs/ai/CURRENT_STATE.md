# Current State — TAB Energy Dashboard

> **Evidence key:** *(verified: path)* = confirmed from file; *(inferred)* = logical deduction; *(assumption)* = unverified.
>
> This document captures active development signals, unfinished work, backup artifacts, and technical debt **as of 2026-08-18**. Update this file when any of these items are resolved.

---

## Aug 2026 audit status (production credibility)

| Task | Description | Status |
|------|-------------|--------|
| **1** | Price Map blank on uniform prices | **DONE** — `app/tabs/price_map_tab.py` on `main` |
| **2** | Verify/pin Streamlit Cloud Python | **OPEN** |
| **3** | Fix launch docs (`streamlit run app/main.py` from root) | **OPEN** |
| **4** | Real EIA-860 coordinates | **DONE** (ETL + `data/eia860_plant_locations.parquet`; **committed `generation.parquet` still stale**) |
| **5** | Fix facility-fuel generation join | **DONE** (ETL code; **parquet not refreshed yet**) |
| **6** | Honest generation labeling | **DONE** — `generation_is_estimated`, no 70% fallback in tab/ETL |
| **7** | Queue freshness labeling | **OPEN** |
| **8** | Dynamic CDR queue source | **OPEN** |
| **9** | Fix `refresh_all_data.sh` | **OPEN** |
| **10** | ETL failure visibility | **DONE** — plants ETL no longer `continue-on-error`; validation step added |
| **11** | Fix workflow commit/push git strategy | **DONE** — concurrency, pull-before-ETL, push retry (`2bac401`) |
| **12** | Reconcile `docs/ai/` | **IN PROGRESS** — this file + `CHANGELOG_FOR_AI.md` |

### Generation data gap (blocker for dashboard credibility)

*(verified: local `data/generation.parquet` inspection, 2026-08-18)*

- 850 rows, **no** `generation_is_estimated` column
- 100% of rows have `actual_generation_mw / capacity_mw == 0.7` (fabricated legacy output)
- W A Parish at `(32.1011, -102.1946)` with gen `1915.76` — not EIA-860 / EIA-923 values

**ETL code on `main` is correct** (`etl/eia_plants_etl.py`: measured generation only, EIA-860 coords, rolling date windows). **CI must run successfully** and commit fresh parquet. After merge of `2bac401`, manually dispatch **Actions → ETL Data Updates → Run workflow** on `main` (or wait for 6-hour schedule). Validation: `python scripts/validate_generation_parquet.py`.

---

## Active development signals

| Signal | Evidence | Source |
|--------|----------|--------|
| `minerals_deposits.parquet` has only 1 row | Sparse data | *(verified: parquet inspection)* |
| `data/ercot_cdr_may2025.xlsx` is a May 2025 snapshot | Filename and content imply staleness | *(verified: filename)* |
| Disabled legacy workflow `.github/workflows/etl-old.yml` | Schedule removed, workflow_dispatch only | *(verified: `.github/workflows/etl-old.yml`)* |
| Committed `generation.parquet` predates P0 ETL fixes | See audit table above | *(verified: parquet inspection)* |

*(Backup files in `app/tabs/` and `.github/workflows/etl.yml.backup` were removed in `a8af0b1`.)*

---

## ETL script status

| Script | Status | Notes |
|--------|--------|-------|
| `etl/eia_fuelmix_etl.py` | **Production** | Paginated EIA API fetch; falls back to demo data without API key |
| `etl/ercot_lmp_etl.py` | **Production** | Scrapes ERCOT public HTML |
| `etl/eia_plants_etl.py` | **Production** | EIA-860 coords + EIA-923 facility-fuel measured generation only; rolling date windows; fails without API key/data |
| `etl/ercot_queue_etl.py` | **Production** | ERCOT CDR Excel parsing |
| `etl/mineral_etl.py` | **Production (sparse)** | Manual curation; polygon generation requires external shapefile |
| `etl/price_map_etl.py` | **Demo stub** | Hardcoded nodes; not called from CI workflow |
| `etl/interconnection_etl.py` | **Empty stub** | Only creates empty queue schema; not called from CI |
| `etl/demo_fuelmix_data.py` | **Fallback** | Synthetic data used when `EIA_API_KEY` is absent |

*(verified: `.github/workflows/etl.yml`, ETL file contents)*

---

## TODO / FIXME items (verified from code)

### `app/tabs/minerals_tab.py` (line 545, 572)
```python
# TODO section for manual updates
# TODO: Implement GeoJSON loading in `etl/mineral_etl.py`
#       when shapefile sources become available.
```
*(verified: `app/tabs/minerals_tab.py`)*

### `README.md` (Contributing section)
Acknowledged unimplemented items:
- Implement real ERCOT price data fetch *(now implemented in `ercot_lmp_etl.py` — README may be outdated)*
- Implement EIA plants data from FeatureServer
- Implement interconnection queue data *(now implemented in `ercot_queue_etl.py`)*
- Add historical data trends
- Add export functionality *(now implemented in `app/utils/export.py`)*
- Add custom date range selection

*(verified: `README.md`)*

---

## Backup and deprecated artifacts

### Files that should not be in production but are committed

| File | Type | Should be resolved by |
|------|------|----------------------|
| `app/main.py.backup` | Backup | Review and delete if safe |
| `app/tabs/minerals_tab.py.auto_backup` | Auto-backup | Review and delete if safe |
| `app/tabs/minerals_tab.py.backup2` | Backup | Review and delete if safe |
| `app/tabs/minerals_tab_OLD_BACKUP.py` | Old backup | Review and delete if safe |
| `etl/ercot_lmp_etl.py.backup` | Backup | Review and delete if safe |
| `.github/workflows/etl-old.yml` | Disabled legacy workflow | Archive or delete |
| `.github/workflows/etl.yml.backup` | Backup | Delete |
| `etl/interconnection_etl.py` | Superseded stub | Remove or replace |
| `etl/price_map_etl.py` | Demo stub (production replaced by `ercot_lmp_etl.py`) | Remove or clarify |

---

## README accuracy issues (verified)

The `README.md` project structure diagram lists several items that are outdated:
- Shows `price_map_etl.py` as "Demo price data" — it is a demo stub but **not** called by CI
- Shows `eia_plants_etl.py` as "Plants stub (TODO)" — it is now implemented as production
- Shows `interconnection_etl.py` as "Queue stub (TODO)" — superseded by `ercot_queue_etl.py`
- Does not mention `minerals_tab.py` or the minerals pipeline
- Color palette table shows old hex codes (e.g., `#fb923c` for Gas) that differ from current `app/utils/colors.py` values (current: `#C8102E`)

*(verified: `README.md`, `app/utils/colors.py`)*

---

## Data staleness risks

| Risk | Details |
|------|---------|
| `data/ercot_cdr_may2025.xlsx` | May 2025 snapshot; queue data may be stale unless CDR download succeeds |
| `minerals_deposits.parquet` has 1 row | Effectively empty; minerals tab will render minimal content |
| ERCOT HTML scraping | ERCOT may change their HTML format, breaking `ercot_lmp_etl.py` |
| LinkedIn CDN logo URL | Logo loaded from LinkedIn CDN at runtime; may break if URL changes |

*(verified from code and data inspection)*

---

## Technical debt

| Item | File | Severity |
|------|------|---------|
| Hardcoded LinkedIn CDN logo URL in `app/main.py` | `app/main.py` | Medium — external URL may break |
| Duplicate/redundant ETL scripts (`price_map_etl.py` vs `ercot_lmp_etl.py`) | `etl/` | Low |
| README project structure is significantly outdated | `README.md` | Low |
| Multiple `.backup` files committed to repository | Various | Low |
| `minerals_deposits.parquet` has only 1 row | `data/` | Medium — minerals tab shows almost nothing |
| `data/ercot_cdr_may2025.xlsx` will become stale | `data/` | Medium |
| `app/utils/schema.py` canonical schema for `queue` uses `fuel`/`proposed_mw` but actual parquet uses `fuel_type`/`capacity_mw` | `app/utils/schema.py` | Medium — column aliases bridge this but creates hidden coupling |
| `etl/interconnection_etl.py` stub not removed | `etl/` | Low |

---

## Confirmed working (as of last ETL run)

- `data/fuelmix.parquet` — 1,384 rows, 4 columns *(verified: parquet inspection)*
- `data/generation.parquet` — 850 rows, 7 columns — **legacy fabricated data; see audit table above** *(verified: parquet inspection)*
- `data/price_map.parquet` — 15 rows (one per settlement point), 11 columns *(verified: parquet inspection)*
- `data/queue.parquet` — 281 rows, 11 columns *(verified: parquet inspection)*

---

## Blockers (evidenced)

1. **Committed `generation.parquet` is stale** — P0 ETL fixes merged but no successful post-fix CI run has committed measured data *(verified: GitHub Actions runs for `72dacd8`/`5f26547`/`2bac401` absent as of 2026-08-18)*. **Action:** dispatch ETL workflow on `main` after `2bac401`.
2. **EIA_API_KEY required for plants ETL** — without it, plants ETL and `scripts/validate_generation_parquet.py` fail in CI *(verified: `etl/eia_plants_etl.py`, workflow)*.
3. **ERCOT HTML format change** — would break `ercot_lmp_etl.py` silently (still `continue-on-error: true` for non-plants ETLs).
4. **Shapefile not available** — polygon overlay for minerals will not be generated *(verified: `etl/mineral_etl.py` comment)*.
