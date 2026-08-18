#!/bin/bash
#
# Refresh All ETL Data Script
# Run from the repository root to update dashboard parquet files.
# Matches the production ETLs in .github/workflows/etl.yml
# (not demo stubs such as etl/price_map_etl.py).
#

set -euo pipefail

echo "=================================================="
echo "🔄 REFRESHING ALL DASHBOARD DATA"
echo "=================================================="
echo ""

cd "$(dirname "$0")"

PYTHON="${PYTHON:-python}"
if [ -x ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
elif [ -x "venv/bin/python" ]; then
    PYTHON="venv/bin/python"
fi

run_etl() {
    local label="$1"
    local script="$2"
    echo "${label}"
    if "${PYTHON}" "${script}"; then
        echo "✅ ${script} completed"
    else
        echo "❌ ${script} failed"
        exit 1
    fi
    echo ""
}

run_etl "1️⃣  Fetching EIA fuel mix data..." "etl/eia_fuelmix_etl.py"
run_etl "2️⃣  Fetching ERCOT real-time settlement prices..." "etl/ercot_lmp_etl.py"
run_etl "3️⃣  Fetching EIA generation plants data..." "etl/eia_plants_etl.py"
run_etl "4️⃣  Processing ERCOT interconnection queue..." "etl/ercot_queue_etl.py"

echo "=================================================="
echo "✅ ALL DATA REFRESHED SUCCESSFULLY"
echo "=================================================="
echo ""
echo "Data files updated:"
ls -lh data/*.parquet
echo ""
echo "You can now run the dashboard:"
echo "  streamlit run app/main.py"
echo ""
