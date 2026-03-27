#!/bin/bash
set -e

python main.py
streamlit run app.py --server.address 0.0.0.0 --server.port 8501