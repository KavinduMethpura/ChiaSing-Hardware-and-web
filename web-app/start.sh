#!/bin/bash
# PlantHead Web App Launcher for Linux / macOS
set -e

cd "$(dirname "$0")"

echo "======================================================"
echo " PlantHead Multi-Device Controller Web App"
echo "======================================================"

if [ ! -d "venv" ]; then
    echo "[1/3] Creating virtual environment..."
    python3 -m venv venv
fi

echo "[2/3] Installing dependencies..."
source venv/bin/activate
pip install -r requirements.txt --quiet

echo "[3/3] Starting Web App on http://localhost:8080 ..."
if which xdg-open > /dev/null; then
    xdg-open http://localhost:8080 &
elif which open > /dev/null; then
    open http://localhost:8080 &
fi

python3 app.py
