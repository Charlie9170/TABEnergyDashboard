#!/bin/bash
# 
# Refresh All ETL Data Script
# Run this to update all dashboard data from APIs
#

echo "=================================================="
echo "🔄 REFRESHING ALL DASHBOARD DATA"
echo "=================================================="
echo ""

cd "$(dirname "$0")"

echo "1️⃣  Fetching EIA fuel mix data..."
python etl/eia_fuelmix_etl.py
if [ $? -eq 0 ]; then
    echo "✅ Fuel mix data refreshed"
else
    echo "❌ Fuel mix ETL failed"
    exit 1
fi
echo ""

echo "2️⃣  Fetching EIA generation plants data..."
python etl/eia_plants_etl.py
if [ $? -eq 0 ]; then
    echo "✅ Generation plants data refreshed"
else
    echo "❌ Plants ETL failed"
    exit 1
fi
echo ""

echo "3️⃣  Processing ERCOT interconnection queue..."
python etl/ercot_queue_etl.py
if [ $? -eq 0 ]; then
    echo "✅ Queue data refreshed"
else
    echo "❌ Queue ETL failed"
    exit 1
fi
echo ""

echo "4️⃣  Generating price map data..."
python etl/price_map_etl.py
if [ $? -eq 0 ]; then
    echo "✅ Price map data refreshed"
else
    echo "❌ Price map ETL failed"
    exit 1
fi
echo ""

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
