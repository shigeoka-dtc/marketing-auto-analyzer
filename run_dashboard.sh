#!/bin/bash
set -euo pipefail

# Dashboard module removed. This script now proxies to worker-only mode.
# Kept for backward compatibility with run.sh and existing usage scripts.

echo "run_dashboard.sh is deprecated and will redirect to run_worker.sh"
if [ -f "./run_worker.sh" ]; then
  exec /bin/bash "./run_worker.sh"
else
  echo "ERROR: run_worker.sh not found. Please restore worker runner."
  exit 1
fi
