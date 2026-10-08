#!/bin/bash
# PlantHead Device Setup Script (Foolproof & Non-Interrupting)
# Run on the Raspberry Pi: bash setup.sh

set -e

echo "=== PlantHead Setup Starting ==="

# 1. Update & Install System Dependencies
echo "[1/5] Installing system packages..."
sudo apt update
sudo apt install -y python3-venv python3-pip python3-numpy swig python3-dev liblgpio-dev \
    i2c-tools rpicam-apps alsa-utils ffmpeg avahi-daemon comitup

# 2. Virtual Environment (with system-site-packages for fast hardware drivers & numpy)
echo "[2/5] Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv --system-site-packages venv
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 3. Ensure Directories Exist
echo "[3/5] Ensuring data and secrets directories exist..."
mkdir -p data/images data/audio data/music logs secrets

# 4. Environment Check
if [ ! -f ".env" ]; then
    echo "[!] No .env file found. Copying .env.example -> .env"
    cp .env.example .env
    echo "[!] Please edit .env with your DEVICE_ID, Adafruit IO, and Drive folder IDs!"
fi

# 5. Register Avahi & Systemd Services (Without dropping network/SSH)
echo "[4/5] Registering Avahi discovery and Systemd background services..."
DEVICE_ID=$(grep '^DEVICE_ID=' .env 2>/dev/null | cut -d '=' -f2 | tr -d ' "\r' || true)
if [ -z "$DEVICE_ID" ]; then
    DEVICE_ID="planthead1"
fi
echo "Using DEVICE_ID: $DEVICE_ID"

# Copy Avahi discovery file (deferred reload prevents Wi-Fi disconnect)
sudo sed "s/planthead1/$DEVICE_ID/g" avahi/planthead.service | sudo tee /etc/avahi/services/planthead.service > /dev/null

# Register and enable Systemd services
sudo cp systemd/planthead.service /etc/systemd/system/
sudo cp systemd/planthead-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable planthead.service
sudo systemctl enable planthead-api.service
sudo systemctl enable avahi-daemon

echo ""
echo "=== [5/5] PlantHead Setup Completed Successfully! ==="
echo ""
echo "Next steps:"
echo "1. Verify .env: nano .env"
echo "2. Ensure secrets/gdrive_token.json is present"
echo "3. Run hardware diagnostics:"
echo "   python3 test_hardware.py"
echo "4. Reboot to start all background services & audio overlay:"
echo "   sudo reboot"
