#!/bin/bash
# Auto-commit helper script
# This script helps prevent data loss by committing data files after ETL runs
# Usage: ./scripts/auto_commit.sh "commit message"

set -e

# Change to project root
cd "$(dirname "$0")/.."

# Check if there are changes
if ! git diff --quiet data/ || ! git diff --cached --quiet data/; then
    # Stage data files
    git add data/*.parquet
    
    # Commit with provided message or default
    MESSAGE="${1:-Auto-update data files ($(date -u '+%Y-%m-%d %H:%M:%S UTC'))}"
    git commit -m "$MESSAGE"
    
    echo "✓ Changes committed: $MESSAGE"
    
    # Optionally push (uncomment if you want auto-push)
    # git push
    # echo "✓ Changes pushed to remote"
else
    echo "ℹ No changes to commit"
fi
