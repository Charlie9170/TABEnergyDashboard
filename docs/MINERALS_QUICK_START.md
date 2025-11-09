# Quick Start: Adding New Mineral Deposits

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

3. **Run the ETL:**
   ```bash
   python etl/mineral_etl.py
   ```

4. **Refresh the dashboard** (it should auto-reload)

## Method 2: Bulk Import from Spreadsheet

1. **Prepare data in Excel/Google Sheets** with the same columns
2. **Export as CSV** and save to `data/manual_mineral_deposits.csv`
3. **Run ETL and refresh** (same as Method 1, steps 3-4)

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
- Yellow/gold marker on map (Exploratory status)
- Medium size (75,000 MT)
- Appears in "Exploratory" status breakdown
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

**Wrong color on map:**
- Check development_status spelling (case-insensitive but must match exactly)
- Clear browser cache and refresh

**ETL fails:**
- Check CSV for malformed rows (extra commas, missing quotes around text with commas)
- Look at `etl_minerals.log` for detailed error messages

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
2. **Uncomment GeoJSON loading** in `etl/mineral_etl.py` (line ~95)
3. **Implement mapping** from GeoJSON properties to required schema
4. **Run ETL** - it will merge with manual CSV
5. **CSV takes precedence** for conflicts (manual overrides automatic)

---

**For Questions:** See full documentation in `docs/MINERALS_TAB_COMPLETE.md`
