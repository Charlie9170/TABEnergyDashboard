#!/bin/bash
# Run the TAB Energy Dashboard

cd "$(dirname "$0")"
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
streamlit run app/main.py
