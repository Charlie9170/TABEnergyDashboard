# 🔑 EIA API Key Setup Guide - GitHub Actions

## ✅ Option A: Use Repository Variables (RECOMMENDED)

GitHub **Variables** are more reliable than Secrets for non-sensitive configuration.

### Step 1: Create Repository Variable (2 minutes)

1. Go to your repository: https://github.com/Charlie9170/TABEnergyDashboard

2. Click: **Settings** → **Secrets and variables** → **Actions**

3. Click the **"Variables"** tab (not "Secrets")

4. Click **"New repository variable"**

5. Enter:
   - **Name**: `EIA_API_KEY`
   - **Value**: `z9d4AvwBK6c8FXmei1kasuD849Mz6i5WALqgQyiV`

6. Click **"Add variable"**

### Step 2: Test the Workflow

1. Go to **Actions** tab

2. Select **"ETL Data Updates"** workflow

3. Click **"Run workflow"** → **"Run workflow"**

4. Watch the logs - you should see:
   ```
   ✅ Using EIA_API_KEY from VARIABLES
      First 8 chars: z9d4AvwB...
      Last 8 chars: ...gQyiV
   ```

### Step 3: Verify Auto-Updates

- Workflow runs automatically every 6 hours
- Check **Actions** tab to see successful runs
- Data files update in `data/*.parquet`

---

## 🔒 Option B: Use Repository Secrets (Alternative)

If you prefer secrets over variables:

### Step 1: Delete Existing Secret (if exists)

1. Go to: **Settings** → **Secrets and variables** → **Actions** → **Secrets** tab

2. Find `EIA_API_KEY` (if it exists)

3. Click **Delete** to remove it

### Step 2: Create New Secret

1. Click **"New repository secret"**

2. Enter:
   - **Name**: `EIA_API_KEY`
   - **Value**: `z9d4AvwBK6c8FXmei1kasuD849Mz6i5WALqgQyiV`

3. Click **"Add secret"**

### Step 3: Test

Same as Option A, Step 2

---

## 🔍 Troubleshooting

### Issue: "No EIA_API_KEY found in secrets or variables"

**Solution:**
- Check you created the variable/secret with exact name: `EIA_API_KEY` (case-sensitive)
- Verify you're in the correct repository: `Charlie9170/TABEnergyDashboard`
- Wait 1-2 minutes after creating variable/secret, then re-run workflow

### Issue: "Context access might be invalid"

This is just a linter warning, ignore it. The workflow will work fine.

### Issue: ETL script says "API key not found"

**Solution:**
Check the diagnostic output in workflow logs:
```
🔍 API Key Diagnostics
Secret EIA_API_KEY length: 40 characters
Variable EIA_API_KEY length: 40 characters
✅ Using EIA_API_KEY from VARIABLES
```

If lengths show `0`, the variable/secret isn't set correctly.

---

## 📊 What Changed in the Workflow

### Before:
```yaml
- name: Run EIA Fuel Mix ETL
  env:
    EIA_API_KEY: ${{ secrets.EIA_API_KEY }}
  run: python etl/eia_fuelmix_etl.py
```

### After:
```yaml
- name: Run EIA Fuel Mix ETL
  run: |
    export EIA_API_KEY="${EIA_API_KEY_SECRET:-$EIA_API_KEY_VAR}"
    if [ -z "$EIA_API_KEY" ]; then
      echo "⚠️  Skipping - No API key available"
      exit 0
    fi
    echo "✅ API key found: ${EIA_API_KEY:0:8}...${EIA_API_KEY: -8}"
    python etl/eia_fuelmix_etl.py
  env:
    EIA_API_KEY_SECRET: ${{ secrets.EIA_API_KEY }}
    EIA_API_KEY_VAR: ${{ vars.EIA_API_KEY }}
```

**Benefits:**
- ✅ Works with both secrets AND variables
- ✅ Clear diagnostics showing which is used
- ✅ Shows first/last 8 chars for verification
- ✅ Graceful skip if no key (doesn't fail workflow)
- ✅ Fallback: tries secret first, then variable

---

## 🎯 Success Criteria

You'll know it's working when:

1. **Actions tab** shows green checkmarks ✅
2. **Workflow logs** show:
   ```
   ✅ Using EIA_API_KEY from VARIABLES
   ✅ API key found: z9d4AvwB...gQyiV
   🔄 Running EIA Fuel Mix ETL...
   ```
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
