# Handoff

Operational notes for whoever maintains the TAB Energy Dashboard next. Every claim
here was checked against the code in this repo on 2026-08-19. Setup detail lives in
`README.md`; this file covers ownership, credentials, and the things that will bite you.

## Ownership

- **GitHub repo:** `https://github.com/Charlie9170/TABEnergyDashboard` — the only
  remote (`origin`). It is a personal account, not a TAB organization account.
- **Streamlit Cloud:** a personal Streamlit Cloud account, signed in through that
  same `Charlie9170` GitHub account. The deployed app is
  `https://tabenergy.streamlit.app/`.

Both are personal accounts. Moving this to a TAB-owned account means transferring the
GitHub repo and re-deploying the app under the new Cloud account — the deployment is
not something you can hand over from inside this repo.

Streamlit Cloud also holds the app's Python version (3.14) in its Advanced settings.
That setting is not in this repo and cannot be changed from here, which is why
`pandas`, `pyarrow`, and `numpy` are pinned to releases that publish cp314 wheels.

## EIA_API_KEY

Two ETLs need it: `etl/eia_fuelmix_etl.py` and `etl/eia_plants_etl.py`. Both read the
`EIA_API_KEY` environment variable first, then fall back to Streamlit secrets.

- **In CI:** GitHub → Settings → Secrets and variables → Actions → `EIA_API_KEY`.
  `.github/workflows/etl.yml` passes it to those two steps only.
- **Replacement key:** register at `https://www.eia.gov/opendata/register.php`. It is
  free and issued immediately by email. Paste the new value into the GitHub secret
  above; nothing in the code needs to change.
- **Locally:** either `export EIA_API_KEY="..."` or put it in
  `.streamlit/secrets.toml`, which is gitignored. Never commit it.

If the key is missing or invalid, both ETLs exit 1 and write nothing, so the last good
data stays in place. Fuel Mix and Generation will simply stop advancing until the key
is fixed. Neither one fabricates data to fill the gap.

## How data refreshes

`.github/workflows/etl.yml` runs every 6 hours (`cron: '0 */6 * * *'`) and can be
triggered by hand from the Actions tab. Each run, in order:

1. Four ETLs: `eia_fuelmix_etl.py`, `ercot_lmp_etl.py` (both `continue-on-error`, so a
   failure is logged but does not stop the run), then `eia_plants_etl.py` and
   `ercot_gis_queue_etl.py` (a failure here fails the job).
2. Two validators gate the commit: `scripts/validate_generation_parquet.py` and
   `scripts/validate_gis_queue_parquet.py`. They only read. If either fails the job
   stops before `git add`, so the last good data on `main` stays untouched. They check
   for empty frames, estimated or fabricated-looking generation values, the status
   enum and Texas coordinate bounds on the queue, and cross-check the queue's row
   count and total MW against the source report's own published totals (15% tolerance).
3. Commit and push: stages `data/*.parquet` and `data/queue_gis_metadata.json`, writes
   a UTC timestamp into `.streamlit_trigger`, and pushes an "Auto-update" commit to
   `main`. `.streamlit_trigger` exists only to guarantee a changed file so Streamlit
   Cloud redeploys; the parquet files are committed to git on purpose — the app reads
   them from the repo, there is no database.

**Minerals is not in CI.** `etl/mineral_etl.py` writes
`data/minerals_deposits.parquet` and is run by hand, then committed. It is a small
manually curated table, so it will simply sit unchanged until someone updates it.

To update it, edit `data/manual_mineral_deposits.csv` — that CSV is the source of
record, it is committed, and it is the only input the script has. Then run
`python etl/mineral_etl.py` from the repo root and commit the regenerated parquet
alongside the CSV. If the CSV is missing or has no rows the script exits non-zero
without writing, so a bad run leaves the existing deposits in place rather than
replacing them with a placeholder.

## When something breaks

- **App errors:** Streamlit Cloud → Manage app → logs. Note that a broken tab is
  invisible on the page: `app/main.py` wraps each tab in `safe_render_tab`, which logs
  the exception and shows "This section is temporarily unavailable" rather than a
  stack trace. The logs are the only place the real error appears.
- **ETL failures:** GitHub → Actions → "ETL Data Updates". **A green checkmark does not
  mean all four ETLs succeeded.** The fuel mix and price map steps run with
  `continue-on-error: true`, so either can fail while the run still reports overall
  success. You have to open the run and expand the individual steps to see it — there
  is no alert, no failed badge, and nothing on the dashboard itself will say so, since
  a failed fuel mix step writes nothing and the tab keeps showing the previous data.
  Expanding those steps is now the primary way a stalled fuel mix refresh gets
  noticed, so check them whenever Fuel Mix looks older than a day or two.
- **Data that looks wrong rather than missing:** the validators' output is printed in
  the run log, including row counts and the queue cross-check percentages.

## Known limitations

- **Fuel Mix always shows a date a day or two back.** EIA's hourly feed publishes
  through the end of the previous Central day. Across the last eight refreshes the
  newest interval was always 04:00 UTC (23:00 CT the day before), trailing the run by
  8 to 26 hours depending on which of the four daily runs you look at. This is the
  source's publication schedule, not a bug in the pipeline.
- **Queue coordinates are approximate.** The ERCOT GIS report publishes no lat/lon at
  all — only a county and a free-text substation description. Coordinates are the
  county centroid plus deterministic jitter of up to about 2 miles, seeded from the
  project name so a project does not move between refreshes
  (`etl/ercot_queue_etl.py`). Dots show which county a project is in, nothing finer.
- **County coverage is incomplete.** `etl/texas_counties.py` has 251 of Texas's 254
  counties. An unknown county falls back to the state centroid (31.0, -99.9) with a
  logged warning, so those projects appear in the middle of Texas. Currently 7 of 1827
  queue rows sit there.
- **Three tests fail in `tests/test_eia_plants_etl.py`** and did so before the cleanup.
  They are stale test expectations, not pipeline breakage: one patches
  `streamlit.secrets.get`, which current Streamlit refuses to allow; one expects a
  numeric-schema error the ETL no longer raises; one feeds an empty frame that now
  trips the coordinate-attach guard. The ETL itself runs in CI every 6 hours behind a
  validator. Fix or delete them, but do not read them as a live defect.
- **Local data goes stale.** CI pushes new parquet to `main` every 6 hours, so your
  working copy falls behind within hours. `git pull` before trusting anything you see
  locally; the deployed site is always at least as fresh.

## Local setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt   # required — an old pyarrow cannot read CI's parquet
streamlit run app/main.py         # from the repo root
```

See `README.md` for the API key step, the ETL commands, and troubleshooting. Do not
run the ETLs casually: they overwrite the committed parquet files in `data/`.

## Contact

Charlie Lamair

- chachacharlie3128@gmail.com — primary, checked indefinitely
- charlielamair2030@u.northwestern.edu — school address, from fall 2026

Genuinely happy to help; I owe these folks a lot. Email either address and I will
answer, including after I have left for school. If something is broken and urgent,
say so in the subject line.
