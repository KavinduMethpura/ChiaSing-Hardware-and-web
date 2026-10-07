#!/bin/bash
# PlantHead Google Drive Authorization Tool
set -e

cd "$(dirname "$0")"

echo "======================================================"
echo " PlantHead Google Drive Authorization Tool"
echo "======================================================"

python3 -m pip install -r requirements.txt
python3 authorize.py
