# Current State — TAB Energy Dashboard

> **Evidence key:** *(verified: path)* = confirmed from file; *(inferred)* = logical deduction; *(assumption)* = unverified.
>
> Active development signals, unfinished work, and technical debt **as of 2026-08-19**.
> Update this file when any item is resolved.

---

## Aug 2026 audit status (production credibility)

| Task | Description | Status |
|------|-------------|--------|
| **1** | Price Map blank on uniform prices | **DONE** — `app/tabs/price_map_tab.py` on `main` |
| **2** | Verify/pin Streamlit Cloud Python | **OPEN** |
| **3** | Fix launch docs (`streamlit run app/main.py` from root) | **DONE** |
| **4** | Real EIA-860 coordinates | **DONE** — in committed `generation.parquet` (CI run 32095361711) |
| **5** | Fix facility-fuel generation join | **DONE** — measured data in committed parquet |
| **6** | Honest generation labeling | **DONE** — `generation_is_estimated`, no 70% fallback in tab/ETL |
| **7** | Queue freshness labeling | **DONE** |
| **8** | Dynamic CDR queue source | **DONE** — replaced with the monthly ERCOT GIS Report (`etl/ercot_gis_queue_etl.py`), merged to `main` in `178fa47` |
| **9** | Fix `refresh_all_data.sh` | **DONE** — calls the production ETLs |
| **10** | ETL failure visibility | **DONE** — plants ETL no longer `continue-on-error`; validation step added |
| **11** | Fix workflow commit/push git strategy | **DONE** — concurrency, pull-before-ETL, push retry (`2bac401`) |
| **12** | Reconcile `docs/ai/` | **DONE** — `CURRENT_STATE.md`, `CHANGELOG_FOR_AI.md` (2026-08-18) |

### Generation data gap (blocker for dashboard credibility)

**Resolved 2026-08-18** — CI run [32095361711](https://github.com/Charlie9170/TABEnergyDashboard/actions/runs/32095361711) committed measured `generation.parquet` on `3e4d0da`:

- 415 rows with `generation_is_estimated` (all `False`)
- No rows with `actual_generation_mw / capacity_mw == 0.7`
- W A Parish at `(29.4828, -95.6311)` with measured generation ~718 MW
- Period columns: `2026-05` to `2026-07` (EIA walk-back from preferred rolling window)

*(verified: GitHub Actions run + raw parquet from `main`, 2026-08-18)*

---

## Active development signals

| Signal | Evidence | Source |
|--------|----------|--------|
| `minerals_deposits.parquet` is sparse (12 rows measured 2026-08-18) | Only dataset with no automated feed | *(verified: parquet inspection, 2026-08-18)* |
| `data/ercot_cdr_may2025.xlsx` is a May 2025 snapshot | Retired — no longer read by the active pipeline; superseded by `etl/ercot_gis_queue_etl.py` (Task 8). File and its ETL (`etl/ercot_queue_etl.py`) left in place, archived. | *(verified: `etl/ercot_gis_queue_etl.py`, `etl/ercot_queue_etl.py` module docstring)* |
| Committed `generation.parquet` predates P0 ETL fixes | Resolved — see audit table above | *(verified: CI run 32095361711)* |

*(All backup files and the legacy `etl-old.yml` workflow have been removed; `.github/workflows/` now contains only `etl.yml`.)*

---

## ETL script status

| Script | Status | Notes |
|--------|--------|-------|
| `etl/eia_fuelmix_etl.py` | **Production** | Paginated EIA API fetch; falls back to demo data without API key |
| `etl/ercot_lmp_etl.py` | **Production** | Scrapes ERCOT public HTML |
| `etl/eia_plants_etl.py` | **Production** | EIA-860 coords + EIA-923 facility-fuel measured generation only; rolling date windows; fails without API key/data |
| `etl/ercot_gis_queue_etl.py` | **Production** | ERCOT GIS Report (monthly); discovers newest report via ERCOT's JSON listing endpoint |
| `etl/ercot_queue_etl.py` | **Deprecated (archived)** | Old CDR pipeline, not run. Still imported by `ercot_gis_queue_etl.py` for its geocoding/atomic-write helpers — do not delete without extracting those first |
| `etl/mineral_etl.py` | **Manual only** | Not in CI; manual curation; polygon generation requires an external shapefile |
| `etl/demo_fuelmix_data.py` | **Fallback** | Synthetic data used when `EIA_API_KEY` is absent |

*(verified: `.github/workflows/etl.yml`, ETL file contents)*

---

## TODO / FIXME items (verified from code)

The only TODOs left in the codebase are three in `etl/mineral_etl.py` (lines 139,
395, 404), all describing the same blocked work: loading mineral polygons from
GeoJSON once a source is available. The minerals pipeline is manual and has no
automated feed. *(verified: `git grep TODO -- 'app/*' 'etl/*' 'scripts/*'`, 2026-08-19)*

`README.md`'s Contributing checklist still lists several items that are in fact
implemented (ERCOT price fetch → `ercot_lmp_etl.py`; interconnection queue →
`ercot_gis_queue_etl.py`; export → `app/utils/export.py`). That list needs pruning.

---

## Backup and deprecated artifacts

**None remain.** Every `.backup` / `.auto_backup` / `_OLD_BACKUP` file and the legacy
`etl-old.yml` workflow were removed in `a8af0b1` and `3377292`; the two superseded ETL
stubs (`price_map_etl.py`, `interconnection_etl.py`) were removed in the Aug 2026
cleanup. Verify with `git ls-files | grep -iE 'backup|old'` before re-adding this
section. *(verified: `git ls-files`, 2026-08-19)*

---

## README accuracy issues (verified)

The setup steps and project-structure block were corrected in the Aug 2026 cleanup and
now match the production ETLs. Remaining known gaps:

- The color palette table still shows old hex codes (`#fb923c` for Gas at `README.md:191`)
  that differ from `app/utils/colors.py` (current: `#C8102E`)
- The Contributing checklist lists several already-implemented items (see TODO section above)

*(verified: `README.md`, `app/utils/colors.py`, 2026-08-19)*

---

## Data staleness risks

| Risk | Details |
|------|---------|
| `minerals_deposits.parquet` is sparse | Manually curated, no automated feed; minerals tab renders limited content |
| ERCOT HTML scraping | ERCOT may change their HTML format, breaking `ercot_lmp_etl.py` |
| LinkedIn CDN logo URL | Logo loaded from LinkedIn CDN at runtime; may break if URL changes |

*(verified from code and data inspection)*

---

## Technical debt

| Item | File | Severity |
|------|------|---------|
| Hardcoded LinkedIn CDN logo URL in `app/main.py` | `app/main.py` | Medium — external URL may break |
| `minerals_deposits.parquet` is sparse and manually curated | `data/` | Medium — minerals tab shows limited content |
| `app/utils/schema.py` canonical schema for `queue` uses `fuel`/`proposed_mw` but actual parquet uses `fuel_type`/`capacity_mw` | `app/utils/schema.py` | Medium — column aliases bridge this but creates hidden coupling (still applies to the GIS pipeline's output) |
| `etl/texas_counties.py` `TEXAS_COUNTY_CENTROIDS` is missing at least one real county ("Sterling") | `etl/texas_counties.py` | Low — falls back to the Texas centroid gracefully (no crash), but those projects render at the state centroid instead of their actual county; discovered running `ercot_gis_queue_etl.py` against the July 2026 GIS Report |

---

## Confirmed working

Row counts below were **measured on 2026-08-18** and change on every ETL refresh —
treat them as a point-in-time sample, not a specification. Read the Parquet for
current values.

| Dataset | Rows (2026-08-18) | Contents |
|---|---|---|
| `fuelmix.parquet` | 1,192 | Hourly ERCOT generation by fuel type |
| `price_map.parquet` | 15 | One row per settlement point (the ERCOT source maximum) |
| `generation.parquet` | 415 | Texas plants with measured EIA-923 generation |
| `eia860_plant_locations.parquet` | 1,367 | EIA-860 plant coordinate reference table |
| `queue.parquet` | 1,827 | ERCOT GIS queue, Large + Small Gen (July 2026 report) |
| `minerals_deposits.parquet` | 12 | Manually curated mineral deposits |

---

## Blockers (evidenced)

1. **ERCOT HTML format change** — would break `ercot_lmp_etl.py` silently (still `continue-on-error: true` for non-plants ETLs).
2. **Shapefile not available** — polygon overlay for minerals will not be generated *(verified: `etl/mineral_etl.py` comment)*.
