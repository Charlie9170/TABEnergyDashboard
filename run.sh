#!/bin/bash
# Run the TAB Energy Dashboard

cd "$(dirname "$0")"
streamlit run app/main.py
