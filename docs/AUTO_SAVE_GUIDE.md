# Auto-Save and Data Protection Guide

This guide explains the auto-save mechanisms in the TAB Energy Dashboard to prevent data loss.

## Problem Context

In the previous attempt, progress was lost when creating a new folder. This dashboard implements multiple layers of protection to prevent data loss:

## 1. GitHub Actions Auto-Commit (Primary Protection)

The GitHub Actions workflow (`.github/workflows/etl.yml`) automatically:
- Runs ETL scripts every 6 hours
- Commits updated data files to the repository
- Pushes changes back to GitHub

This ensures data is **always backed up to GitHub** without manual intervention.

### How it works:

```yaml
- name: Commit and push changes
  run: |
    git config --local user.email "github-actions[bot]@users.noreply.github.com"
    git config --local user.name "github-actions[bot]"
    git add data/*.parquet
    git commit -m "Auto-update data files ($(date -u '+%Y-%m-%d %H:%M:%S UTC'))"
    git push
```

## 2. Data Files in Git (with .gitignore patterns)

The `.gitignore` file is configured to:
- Exclude `data/*.parquet` from version control (since they're generated)
- BUT the GitHub Actions workflow explicitly commits them
- This prevents accidental local commits while ensuring Actions saves them

**Important**: If you manually run ETL scripts locally, use the auto-commit helper script.

## 3. Manual Auto-Commit Helper Script

For local development, use `scripts/auto_commit.sh`:

```bash
# After running ETL scripts locally
./scripts/auto_commit.sh "Manual data update"

# Or let it use the default timestamp message
./scripts/auto_commit.sh
```

This script:
- Checks for changes in data/
- Stages only parquet files
- Commits with a timestamp
- (Optional) Pushes to remote

## 4. Validation Before Commit

The GitHub Actions workflow runs `scripts/validate_data.py` before committing:
- Ensures data files have correct schema
- Validates data types
- Checks for required columns
- Only commits if validation passes

This prevents corrupted data from being saved.

## 5. Data Recovery Strategy

If data is lost locally:

### Recover from GitHub
```bash
# Pull latest data from GitHub
git pull origin main

# Or reset to last known good state
git checkout origin/main -- data/
```

### Regenerate from APIs
```bash
# EIA Fuel Mix (requires API key)
export EIA_API_KEY="your_key_here"
python etl/eia_fuelmix_etl.py

# Demo data (no API key needed)
python etl/price_map_etl.py
python etl/eia_plants_etl.py
python etl/interconnection_etl.py
```

## 6. Best Practices

### Local Development
1. **Always work in a branch**: `git checkout -b feature/my-changes`
2. **Commit frequently**: Use the auto-commit script after ETL runs
3. **Push regularly**: `git push origin your-branch`
4. **Never delete data/ manually**: Use `git clean` or regenerate via ETL

### Production Setup
1. **Enable GitHub Actions**: Ensure workflows have write permissions
2. **Set API keys in Secrets**: Settings → Secrets and variables → Actions
3. **Monitor workflow runs**: Check Actions tab for failures
4. **Set up notifications**: Get alerts if workflows fail

## 7. Automated Backup Schedule

The GitHub Actions workflow runs:
- **Every 6 hours**: `cron: '0 */6 * * *'`
- **Manual trigger**: Via workflow_dispatch
- **On push**: (Optional) Trigger on code changes

You can modify the schedule in `.github/workflows/etl.yml`:

```yaml
on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours
    # - cron: '0 * * * *'   # Every hour
    # - cron: '0 0 * * *'   # Daily at midnight
  workflow_dispatch:  # Manual trigger
```

## 8. Emergency Recovery Commands

### If you accidentally delete data/
```bash
# Restore from git
git checkout HEAD -- data/

# Or pull from remote
git pull origin main
```

### If you lose uncommitted work
```bash
# Check git reflog
git reflog

# Restore from a previous state
git reset --hard HEAD@{1}
```

### If GitHub Actions fails
1. Check the workflow run logs in GitHub Actions tab
2. Look for ETL script errors or API failures
3. Fix the issue and manually trigger the workflow
4. Or run ETL locally and commit manually

## 9. Pre-commit Hooks (Optional)

For additional protection, you can set up git pre-commit hooks:

```bash
# Create .git/hooks/pre-commit
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
# Run data validation before any commit
python scripts/validate_data.py
EOF

chmod +x .git/hooks/pre-commit
```

## 10. Monitoring and Alerts

Set up GitHub notifications:
1. Go to repository Settings → Notifications
2. Enable "Actions" notifications
3. You'll receive emails if workflows fail

Consider adding a status badge to README:
```markdown
![ETL Status](https://github.com/Charlie9170/TABEnergyDashboard/actions/workflows/etl.yml/badge.svg)
```

## Summary

With these mechanisms in place:
- ✅ Data is automatically backed up every 6 hours to GitHub
- ✅ Local changes can be easily committed via helper script
- ✅ Data validation ensures only good data is committed
- ✅ Multiple recovery options if something goes wrong
- ✅ No manual intervention required for production updates

**The key difference from your previous attempt**: GitHub Actions now handles commits and pushes automatically, so you don't lose work even if you delete local folders.
