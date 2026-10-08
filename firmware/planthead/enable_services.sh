#!/bin/bash
# Standalone Service Registration Script for PlantHead
# Run anytime to configure/enable background services without re-running apt or pip:
# bash enable_services.sh

set -e

cd "$(dirname "$0")"

echo "=== Registering PlantHead Services ==="

# Get DEVICE_ID from .env
DEVICE_ID=$(grep '^DEVICE_ID=' .env 2>/dev/null | cut -d '=' -f2 | tr -d ' "\r' || true)
if [ -z "$DEVICE_ID" ]; then
    DEVICE_ID="planthead1"
fi
echo "Configuring for DEVICE_ID: $DEVICE_ID"

# 1. Avahi Discovery Service
echo "[1/3] Configuring Avahi discovery broadcast..."
sudo sed "s/planthead1/$DEVICE_ID/g" avahi/planthead.service | sudo tee /etc/avahi/services/planthead.service > /dev/null

# 2. Copy and Enable Systemd Services
echo "[2/3] Registering systemd background services..."
sudo cp systemd/planthead.service /etc/systemd/system/
sudo cp systemd/planthead-api.service /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable planthead.service
sudo systemctl enable planthead-api.service
sudo systemctl enable avahi-daemon

# 3. Start or status
echo "[3/3] Starting services..."
sudo systemctl restart avahi-daemon || true
sudo systemctl restart planthead.service || true
sudo systemctl restart planthead-api.service || true

echo ""
echo "=== Services Registered & Started! ==="
echo "Check status anytime with:"
echo "  sudo systemctl status planthead.service"
echo "  sudo systemctl status planthead-api.service"
