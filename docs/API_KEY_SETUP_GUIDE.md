# 🔑 EIA API Key Setup Guide - GitHub Actions

## Use Repository Secrets

The EIA API key is a credential, not a configuration value — it authenticates
requests to EIA's API under your registered identity. GitHub **Secrets** are
the correct storage mechanism: they are masked in Actions logs and never
displayed again after creation, unlike **Variables**, which are stored and
displayed in plaintext. The active workflow (`.github/workflows/etl.yml`)
reads `secrets.EIA_API_KEY` exclusively — do not create a Variable of the
same name, it will not be used and only adds confusion.

### Step 1: Create/Update the Repository Secret

1. Go to your repository: https://github.com/Charlie9170/TABEnergyDashboard

2. Click: **Settings** → **Secrets and variables** → **Actions** → **Secrets** tab

3. If `EIA_API_KEY` already exists, click it → **Update** with the new value.
   Otherwise, click **"New repository secret"**.

4. Enter:
   - **Name**: `EIA_API_KEY`
   - **Value**: `<your-eia-api-key>` (get one at https://www.eia.gov/opendata/register.php)

5. Click **"Add secret"** (or **"Update secret"**)

### Step 2: Test the Workflow

1. Go to **Actions** tab
2. Select **"ETL Data Updates"** workflow
3. Click **"Run workflow"** → **"Run workflow"**
4. Confirm the "Run EIA Fuel Mix ETL" and "Run EIA Plants ETL" steps succeed
   without a 401/403 error. GitHub automatically redacts the secret value
   from all log output, so you will not (and should not expect to) see it
   printed anywhere.

### Step 3: Verify Auto-Updates

- Workflow runs automatically every 6 hours
- Check **Actions** tab to see successful runs
- Data files update in `data/*.parquet`

---

## � Troubleshooting

### Issue: ETL step fails with an authentication error

**Solution:**
- Check the secret name is exactly `EIA_API_KEY` (case-sensitive)
- Verify you're in the correct repository: `Charlie9170/TABEnergyDashboard`
- Wait 1-2 minutes after updating the secret, then re-run the workflow
- Confirm the key is valid by testing it locally: `EIA_API_KEY=<key> python etl/eia_fuelmix_etl.py`

### Issue: "Context access might be invalid"

This is just a linter warning, ignore it. The workflow will work fine.

---

## 🎯 Success Criteria

You'll know it's working when:

1. **Actions tab** shows green checkmarks ✅
2. **Workflow logs** show the ETL steps completing without an
   authentication error (GitHub redacts the secret value itself,
   so you will not see it printed — that's expected and correct)
3. **Data files** get updated every 6 hours
4. **Dashboard** shows fresh data

---

## 📅 Next Steps

After successful setup:

1. ✅ Workflow runs automatically every 6 hours
2. ✅ Data updates pushed to GitHub
3. ✅ Dashboard auto-reloads with fresh data
4. ✅ No manual intervention needed!

---

## 🆘 Still Not Working?

If you've tried both options and it still fails:

1. **Check workflow logs** in Actions tab
2. **Look for the diagnostic section** to see what's detected
3. **Verify API key value** has no extra spaces or newlines
4. **Try manual workflow run** to see detailed error messages

---

**Created:** 2025-11-10  
**Status:** Ready to implement  
**Estimated time:** 5 minutes  
**Difficulty:** ⭐ Easy
