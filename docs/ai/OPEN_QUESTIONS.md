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

### OQ-002: ~~Is `etl/price_map_etl.py` still needed?~~ — RESOLVED 2026-08-19

No. It was a demo stub writing hardcoded nodes to `data/price_map.parquet` — the same
path the production `etl/ercot_lmp_etl.py` writes. **Deleted.** Running it would have
overwritten live prices with demo values, and `README.md` listed it as a setup step
until this cleanup.

---

### OQ-003: ~~Is `etl/interconnection_etl.py` still needed?~~ — RESOLVED 2026-08-19

No. **Deleted.** It was an empty stub whose `main()` wrote a zero-row frame over
`data/queue.parquet`, and `README.md` listed it as a setup step — following the
documented setup destroyed the queue dataset. Production is `etl/ercot_gis_queue_etl.py`.

---

### OQ-004: ~~How does `ercot_queue_etl.py` download the latest CDR?~~ — MOOT 2026-08-19

No longer relevant. The CDR pipeline used a single hardcoded URL to a May 2025 file
and never fetched anything newer, which is what motivated the replacement.

The current pipeline (`etl/ercot_gis_queue_etl.py`) resolves the newest report at run
time instead of hardcoding a URL: it queries ERCOT's public document-listing endpoint
for report type 15933, filters to documents whose `FriendlyName` starts with
`GIS_Report_`, and downloads the one with the latest `PublishDate`. Filename-based
construction was rejected because ERCOT's month naming is inconsistent
(`GIS_Report_July2026` vs `GIS_Report_Jun2026`).

*(verified: `etl/ercot_gis_queue_etl.py`)*

---

### OQ-005: Why is `minerals_deposits.parquet` sparse?

Measured at **12 rows on 2026-08-18** — the "only 1 row" figure repeated in earlier
docs was stale. The dataset is small because it is hand-curated: `etl/mineral_etl.py`
is not in CI and there is no automated feed (see `docs/MINERALS_DATA_SOURCES.md` for
why USGS MRDS was unusable).

**Remaining question:** is 12 the intended full set, or a partial load?

**Status:** Partially resolved — count verified, completeness not.

---

### OQ-006: Does `etl/eia_plants_etl.py` use the correct EIA endpoint?

The script docstring says "EIA v2 API - Operating Generator Capacity" but the exact endpoint URL was not confirmed in code inspection (the file was too large to read in full).

**Question:** What is the exact EIA v2 endpoint URL used by `eia_plants_etl.py`?

**Status:** Partially unresolved — confirm from `etl/eia_plants_etl.py`.

---

## Architecture

### OQ-007: ~~What is the Streamlit Cloud application URL?~~ — RESOLVED 2026-08-19

`https://tabenergy.streamlit.app/`, now recorded in `README.md` and
`docs/HANDOFF.md`. It was absent from every repository file, so it came from the repo
owner rather than from code.

---

### OQ-008: ~~Is `data/mineral_polygons_v2.json` used and how?~~ — RESOLVED 2026-08-19

Yes. `load_polygon_data()` in `app/tabs/minerals_tab.py` reads it at runtime as a
GeoJSON FeatureCollection to draw formation overlays on the deposit map, falling back
to `data/mineral_polygons.json` and then to no overlay if neither exists. `.gitignore`
now carries an explicit `!data/mineral_polygons_v2.json` negation, so the file is no
longer merely tracked-in-spite-of `data/*.json`.
*(verified: `app/tabs/minerals_tab.py`, `.gitignore`)*

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

### OQ-010: ~~What does `scripts/auto_commit.sh` do?~~ — RESOLVED 2026-08-19

Read in full (27 lines). It is a local convenience wrapper: `cd`s to the repo root,
checks whether `data/` has changes, and if so runs `git add data/*.parquet` and
`git commit` with an optional message. The push is commented out, so it never
touches the remote.

Safe to run — it only stages `data/*.parquet` and cannot push. It overlaps with the
commit step in `.github/workflows/etl.yml` but does not conflict: CI commits its own
ETL output, this is for committing data after a manual local ETL run. Nothing in the
repository invokes it automatically.

*(verified: `scripts/auto_commit.sh`)*

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
