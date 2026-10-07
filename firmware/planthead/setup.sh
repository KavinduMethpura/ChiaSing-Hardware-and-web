#!/bin/bash
# PlantHead Device Setup Script
# Run on the Raspberry Pi: bash setup.sh

set -e

echo "=== PlantHead Setup Starting ==="

# 1. Update & Install System Dependencies
echo "[1/6] Installing system packages..."
sudo apt update
sudo apt install -y python3-venv python3-pip swig python3-dev liblgpio-dev \
    i2c-tools rpicam-apps alsa-utils ffmpeg avahi-daemon comitup

# 2. Virtual Environment
echo "[2/6] Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 3. Directories
echo "[3/6] Ensuring data and secrets directories exist..."
mkdir -p data/images data/audio data/music logs secrets

# 4. Environment Check
if [ ! -f ".env" ]; then
    echo "[!] No .env file found. Copying .env.example -> .env"
    cp .env.example .env
    echo "[!] Please edit .env with your DEVICE_ID, Adafruit IO, and Drive folder IDs!"
fi

# 5. Avahi mDNS Service Setup
echo "[4/6] Configuring Avahi discovery service..."
DEVICE_ID=$(grep '^DEVICE_ID=' .env | cut -d '=' -f2 | tr -d ' "\r')
if [ -z "$DEVICE_ID" ]; then
    DEVICE_ID="planthead1"
fi
echo "Using DEVICE_ID: $DEVICE_ID"

sudo sed "s/planthead1/$DEVICE_ID/g" avahi/planthead.service | sudo tee /etc/avahi/services/planthead.service > /dev/null
sudo systemctl restart avahi-daemon

# 6. Systemd Services Setup
echo "[5/6] Registering Systemd services..."
sudo cp systemd/planthead.service /etc/systemd/system/
sudo cp systemd/planthead-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable planthead.service
sudo systemctl enable planthead-api.service

echo "=== PlantHead Setup Completed ==="
echo "Next steps:"
echo "1. Verify .env: nano .env"
echo "2. Ensure secrets/gdrive_token.json is present"
echo "3. Start services:"
echo "   sudo systemctl start planthead.service"
echo "   sudo systemctl start planthead-api.service"
