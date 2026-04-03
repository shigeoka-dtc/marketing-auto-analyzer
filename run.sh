#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f "./run_dashboard.sh" ]; then
  echo "run_dashboard.sh found: using dashboard-compatible runner"
  exec /bin/bash "./run_dashboard.sh"
elif [ -f "./run_worker.sh" ]; then
  echo "run_dashboard.sh not found. Falling back to run_worker.sh"
  exec /bin/bash "./run_worker.sh"
else
  echo "ERROR: run_dashboard.sh and run_worker.sh are missing. Cannot continue."
  exit 1
fi
