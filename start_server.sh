#!/usr/bin/env bash
# OpsCommand — Operations & Logistics Command Portal Launcher
set -e

cd "$(dirname "$0")"
echo "========================================================"
echo "  OpsCommand Operations & Logistics Portal (Port 8000)"
echo "  URL: http://127.0.0.1:8000"
echo "========================================================"
python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
