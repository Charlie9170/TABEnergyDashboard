# Quick Start: Adding New Mineral Deposits

`data/manual_mineral_deposits.csv` is the committed source of record for this dataset
and the only input the ETL has. Edit it, rerun the ETL, and commit both the CSV and
the regenerated parquet.

## Method 1: Edit CSV Directly (Recommended)

1. **Open the CSV file:**
   ```bash
   open data/manual_mineral_deposits.csv
   ```

2. **Add a new row with these columns:**
   - `deposit_name` - Name of the site (e.g., "West Texas Lithium Mine")
   - `lat` - Latitude in decimal degrees (e.g., 31.5000)
   - `lon` - Longitude in decimal degrees (e.g., -100.2500)
   - `minerals` - Comma-separated list (e.g., "Lithium, REEs")
   - `estimated_tonnage` - Number in metric tons (or 0 for TBD)
   - `development_status` - One of: Major, Early, Exploratory, Discovery
   - `county` - Texas county name (e.g., "Harris")
   - `details` - Description and notes (can be long)

3. **Run the ETL** from the repository root — it resolves `data/` relative to the
   working directory:
   ```bash
   python etl/mineral_etl.py
   ```

4. **Refresh the dashboard** (it should auto-reload)

5. **Commit the CSV and `data/minerals_deposits.parquet` together** — nothing in CI
   regenerates minerals

## Method 2: Bulk Import from Spreadsheet

1. **Prepare data in Excel/Google Sheets** with the same columns
2. **Export as CSV** and save to `data/manual_mineral_deposits.csv`
3. **Run ETL and refresh** (same as Method 1, steps 3-5)

An export replaces the whole file, so keep all eight columns and every existing row —
the ETL has no other copy of them.

## Development Status Guide

### Major Development
Sites with active large-scale operations or construction:
- Round Top Mountain (multiple REEs)
- Smackover Formation (lithium)
- Large investment commitments ($100M+)
- Production timeline within 2-3 years

### Early Development  
Initial operations or pilot facilities:
- Helium extraction plants
- Zinc operations
- Production has started but limited scale
- Proven reserves, developing infrastructure

### Exploratory
Active geological surveys and feasibility studies:
- Brewster County REE surveys
- Cave Peak molybdenum deposit
- Drilling/sampling underway
- Resource estimates being refined

### Discovery
Initial prospecting and identification:
- Dell City USGS surveys
- Sierra Blanca beryllium occurrences
- Potential identified but not quantified
- Early-stage investigation

## Example: Adding a New Deposit

**Scenario:** USGS discovers new lithium deposit in Midland County

**CSV Row:**
```csv
West Midland Lithium,31.9973,-102.0779,Lithium,75000,Exploratory,Midland,"USGS survey identified lithium-bearing brines in Permian Basin formation. Initial estimates suggest 75,000 MT recoverable lithium. Exploratory drilling planned for 2026."
```

**Result:**
- A marker on the map, sized from the tonnage — every deposit marker is the same
  translucent gray regardless of status (`app/tabs/minerals_tab.py`)
- Counted under "Exploratory" in the legend and the status breakdown
- Searchable by "Lithium" mineral filter
- Shows in data table with full details

## Coordinate Tips

**Finding Coordinates:**
1. **Google Maps:** Right-click location → "What's here?" → Copy lat/lon
2. **County Centroid:** If exact location unknown, use county center
3. **Format:** Decimal degrees (not degrees/minutes/seconds)
4. **Texas Bounds:** 
   - Latitude: 25.84 to 36.50
   - Longitude: -106.65 to -93.51

**Common Texas Coordinates:**
- El Paso: 31.7619, -106.4850
- Houston: 29.7604, -95.3698
- Dallas: 32.7767, -96.7970
- San Antonio: 29.4241, -98.4936
- Austin: 30.2672, -97.7431

## Troubleshooting

**Deposit not appearing:**
- Check coordinates are within Texas bounds
- Verify CSV has no blank required fields
- Ensure development_status is exactly Major/Early/Exploratory/Discovery

**Wrong status shown:**
- Marker color does not encode status, so check the legend swatch and count instead
- `development_status` is title-cased before matching, but anything outside Major /
  Early / Exploratory / Discovery is silently rewritten to `Exploratory` with a
  warning in the log — check spelling if a deposit lands in the wrong bucket
- Clear browser cache and refresh

**ETL fails:**
- Check CSV for malformed rows (extra commas, missing quotes around text with commas)
- Look at `etl_minerals.log` for detailed error messages. It is written to whatever
  directory you ran the script from, and is gitignored
- "Manual deposits CSV not found" or "contains no deposit rows" means the script
  stopped on purpose without writing, leaving the existing parquet untouched. Restore
  `data/manual_mineral_deposits.csv` (it is committed) and rerun

## Updating Existing Deposits

1. **Find the row** in CSV
2. **Edit the values** (e.g., increase tonnage, change status)
3. **Run ETL** to regenerate parquet
4. **Refresh dashboard** to see changes

**Example:** Upgrade Dell City from Discovery to Exploratory:
```csv
# Before:
Dell City USGS Survey,31.9286,-105.2050,"REEs (Potential)",0,Discovery,Hudspeth,"..."

# After:
Dell City USGS Survey,31.9286,-105.2050,"REEs (Potential)",50000,Exploratory,Hudspeth,"USGS completed Phase 2 drilling. Updated estimates at 50,000 MT REEs."
```

## Data Quality Checklist

Before running ETL, verify:
- [ ] All coordinates are in Texas
- [ ] Tonnage is numeric (or 0)
- [ ] Status is one of 4 valid values
- [ ] No duplicate deposit names + locations
- [ ] Details field provides context
- [ ] Mineral names are clear (use commas to separate)

## Advanced: Integrating External Data

**When GeoJSON/shapefile sources become available:**

1. **Place file** in `data/mineral_deposits.geojson`
2. **Uncomment the `load_geojson_deposits` call** in `main()` in `etl/mineral_etl.py`,
   next to the `geojson_df` / `combined_df` lines
3. **Implement mapping** from GeoJSON properties to required schema
4. **Run ETL** - it will merge with manual CSV
5. **CSV takes precedence** for conflicts (manual overrides automatic)

---

**For Questions:** See `docs/MINERALS_DATA_SOURCES.md` for data provenance and
sourcing methodology, and `docs/ai/ARCHITECTURE.md` for how the minerals tab fits
the wider application.
