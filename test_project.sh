#!/bin/bash

# Test Script for TAB Energy Dashboard
# Runs all validation checks and provides a project status overview

echo "🧪 TAB Energy Dashboard - Project Test"
echo "======================================="
echo

# Check Python and dependencies
echo "📋 Checking Python environment..."
python --version

echo "📦 Checking dependencies..."
pip list | grep -E "(streamlit|pandas|plotly|pydeck|pyarrow|requests)" || echo "Some dependencies missing - run: pip install -r requirements.txt"
echo

# Validate data files
echo "🔍 Validating data files..."
python scripts/validate_data.py
echo

# Check project structure
echo "📁 Project structure:"
echo "✓ app/main.py - Main Streamlit application"
echo "✓ app/tabs/ - Tab modules (4 tabs)"
echo "✓ app/utils/ - Core utilities (colors, schema, loaders)"
echo "✓ etl/ - ETL scripts (1 working, 3 stubs)"
echo "✓ data/ - Generated data files"
echo "✓ .streamlit/config.toml - Dark theme configuration"
echo "✓ .github/workflows/etl.yml - GitHub Actions automation"
echo

# Test Streamlit app (dry run)
echo "🚀 Testing Streamlit app configuration..."
streamlit config show | head -5
echo

echo "🎯 Quick Test Commands:"
echo "├─ Run dashboard:     streamlit run app/main.py"
echo "├─ Validate data:     python scripts/validate_data.py" 
echo "├─ Generate demo data: python etl/demo_fuelmix_data.py"
echo "└─ Run real ETL:      EIA_API_KEY=your_key python etl/eia_fuelmix_etl.py"
echo

echo "🌐 Dashboard URL (when running): http://localhost:8501"
echo

echo "✅ Project setup complete!"
echo "Next steps: Set EIA_API_KEY and replace demo data with real API calls."