# PlantHead Device Firmware (Pi Zero 2 W)

> [!NOTE]
> For the comprehensive end-to-end multi-device deployment guide (SD card flashing, comitup setup, Avahi discovery, and multi-country relocation), please refer to the master documentation:
> **[firmware/README.md](../README.md)**

---

## Directory Structure

```
planthead/
├── .env.example              # Environment variables template (DEVICE_ID, Adafruit IO, Drive IDs)
├── config.py                 # Central configuration for sensors, intervals, and API settings
├── main.py                   # Data collection daemon (Soil + Camera + Mic continuous recording)
├── api.py                    # Local Flask REST API (/status, /tracks, /play, /stop)
├── gdrive_client.py          # Google Drive OAuth client (upload, list tracks, download cache)
├── io_client.py              # Adafruit IO REST client wrapper
├── requirements.txt          # Python dependencies
├── setup.sh                  # Automation script for quick installation on Raspberry Pi
│
├── audio/
│   ├── mic_recorder.py       # Continuous segmented ambient recording (arecord)
│   ├── speaker_player.py     # Background audio player for MAX98357A I2S mono amplifier
│   └── audio_features.py     # RMS and onset event feature extraction
│
├── camera/
│   └── camera_capture.py     # 1-minute interval still capture via rpicam-still
│
├── sensors/
│   └── soil_sensor.py        # STEMMA Soil Sensor I2C driver & local CSV logger
│
├── avahi/
│   └── planthead.service     # Avahi mDNS service broadcast file (_planthead._tcp, port 5000)
│
├── systemd/
│   ├── planthead.service     # Systemd unit for data collection daemon
│   └── planthead-api.service # Systemd unit for local playback API
│
├── data/                     # Local data cache
│   ├── images/               # Captured snapshots
│   ├── audio/                # Recorded ambient audio segments
│   └── music/                # Downloaded music tracks from Google Drive
│
├── logs/                     # System logs
└── secrets/                  # OAuth tokens (e.g., gdrive_token.json)
```

---

## Quick Start on the Pi

### 1. Run Setup Script
```bash
chmod +x setup.sh
./setup.sh
```

### 2. Configure Environment (`.env`)
```bash
cp .env.example .env
nano .env
```
Fill in your `DEVICE_ID` (e.g. `planthead1`), Adafruit IO credentials, and Google Drive folder IDs.

### 3. Place Google Drive Token
Ensure `secrets/gdrive_token.json` is copied to the Pi.

### 4. Start Services
```bash
sudo systemctl start planthead.service
sudo systemctl start planthead-api.service
```

### 5. Check Service Status & Logs
```bash
sudo systemctl status planthead.service
sudo systemctl status planthead-api.service
journalctl -u planthead-api.service -f
```
