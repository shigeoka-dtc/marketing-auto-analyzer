#!/bin/bash
set -e

export STREAMLIT_CONFIG_DIR=/app/.streamlit
mkdir -p "$STREAMLIT_CONFIG_DIR"

exec streamlit run app.py \
  --server.address 0.0.0.0 \
  --server.port 8501 \
  --browser.gatherUsageStats=false \
  --logger.level=error
