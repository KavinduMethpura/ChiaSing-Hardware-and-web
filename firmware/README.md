# PlantHead — Master Deployment & Setup Guide (Pi Zero 2 W)

This guide walks you through the entire end-to-end process of setting up, deploying, and relocating **PlantHead** units (from 1 to 5 devices).

---

## System Architecture Overview

```
                      [ Adafruit IO ]
                             ▲
                    Soil (30s)| Telemetry
                             │
[ Raspberry Pi Zero 2 W ] ───┼──► [ Google Drive Images Folder ] (1 min still photo)
 (planthead1 .. 5)           ├──► [ Google Drive Audio Folder ]  (continuous 60s ambient)
   │                         └──◄ [ Google Drive Music Folder ]  (shared track library)
   │
   ├── comitup          ──► Hotspot fallback for zero-code Wi-Fi setup anywhere in the world
   ├── avahi-daemon     ──► Broadcasts `_planthead._tcp` with device_id on local network
   ├── planthead.service    (Soil + Camera + Mic continuous data collection daemon)
   └── planthead-api.service (Flask API on port 5000: /status, /tracks, /play, /stop)
         ▲
         │ Local HTTP calls & Zeroconf Discovery
         │
[ Laptop Web App (same Wi-Fi) ] ── Auto-discovers all units, displays status, streams music
```

---

## 1. Preparing & Flashing the SD Card (Initial Setup)

You can configure the initial Wi-Fi and SSH during the flashing step so the Pi connects to your local network automatically on first boot.

1. Insert your MicroSD card into your computer.
2. Open **Raspberry Pi Imager**:
   - **Device**: `Raspberry Pi Zero 2 W`
   - **Operating System**: `Raspberry Pi OS (other)` -> **`Raspberry Pi OS Lite (64-bit)`** (Bookworm recommended).
   - **Storage**: Select your MicroSD card.
3. Click **Next** -> Click **Edit Settings** (or the gear icon):
   - **Hostname**: `planthead1` (for device 1; use `planthead2` for unit 2, etc.)
   - **Set username and password**:
     - Username: `planthead1` (or `pi`)
     - Password: Choose a secure password (e.g., `planthead123`)
   - **Configure wireless LAN**:
     - SSID: Your current home / office Wi-Fi name
     - Password: Your current Wi-Fi password
     - Wireless LAN country: Select your country code (e.g., `AU`, `US`, `GB`)
     > [!IMPORTANT]
     > The Raspberry Pi Zero 2 W **only supports 2.4 GHz Wi-Fi** (802.11 b/g/n). Ensure your Wi-Fi router broadcasts a 2.4 GHz network, not 5 GHz only.
   - **Services tab**: Check **Enable SSH** (Use password authentication).
4. Save settings and click **Write**.
5. Once writing is complete, eject the SD card and insert it into the Pi Zero 2 W.
6. Power on the Pi using a 5V power supply or the PowerBoost 1000C.
7. Wait ~2 minutes for the initial boot and filesystem expansion.
8. Connect from your laptop terminal via SSH:
   ```bash
   ssh planthead1@planthead1.local
   # (or find the Pi's IP address on your router and run: ssh planthead1@<IP>)
   ```

---

## 2. Hardware Wiring & Pi Interface Configuration

### Hardware Pinout Matrix

| Peripheral Component | Function / Pin | Physical Pin | Pi BCM / Header Label | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **PowerBoost 1000C** | 5V Output | Pin 2 or 4 | 5V Power | Powers the Pi from LiPo / USB |
| | GND | Pin 6 | Ground | Common system ground |
| **STEMMA Soil Sensor (I2C)** | VIN | Pin 1 | 3.3V Power | Dedicated 3.3V rail |
| | GND | Pin 9 | Ground | |
| | SDA | Pin 3 | GPIO 2 (I2C1 SDA) | Hardware I2C data |
| | SCL | Pin 5 | GPIO 3 (I2C1 SCL) | Hardware I2C clock |
| **INMP441 Microphone (I2S)** | VDD | Pin 17 | 3.3V Power | Separate 3.3V rail from soil sensor |
| | GND | Pin 14 | Ground | |
| | L/R | Pin 20 / GND | Ground | Selects left channel |
| | WS (Word Select) | Pin 35 | GPIO 19 (PCM_FS) | Shared with amp LRC |
| | SCK (Bit Clock) | Pin 12 | GPIO 18 (PCM_CLK) | Shared with amp BCLK |
| | SD (Serial Data) | Pin 38 | GPIO 20 (PCM_DIN) | Audio input into Pi |
| **MAX98357A Amp (I2S)** | VIN | Pin 2 or 4 | 5V Power | 5V supply for audio amp |
| | GND | Pin 6 / any GND | Ground | |
| | BCLK | Pin 12 | GPIO 18 (PCM_CLK) | Shared with mic SCK |
| | LRC | Pin 35 | GPIO 19 (PCM_FS) | Shared with mic WS |
| | DIN | Pin 40 | GPIO 21 (PCM_DOUT) | Audio output from Pi |
| | SD | Floating | *(Unconnected)* | Floating mixes L+R to mono |
| | Speaker +/- | Speaker Terminals | 4Ω 3W Speaker | Mono speaker |
| **Camera Module** | CSI Ribbon | CSI Port | Dedicated CSI Port | Use 22-pin Pi Zero ribbon cable |

### Enabling Interfaces on the Pi
SSH into the Pi and run:
```bash
sudo raspi-config
```
1. Go to **Interface Options** -> **I2C** -> select **Yes** to enable.
2. Exit `raspi-config`.

### Enabling I2S Audio Overlay
Edit the boot configuration:
```bash
sudo nano /boot/firmware/config.txt
# (On older Bullseye OS, use: sudo nano /boot/config.txt)
```
Add the following line under the `[all]` section:
```ini
# Enable I2S sound card overlay for INMP441 mic and MAX98357A amp
dtoverlay=googlevoicehat-soundcard
```
Reboot the Pi:
```bash
sudo reboot
```

---

## 3. Transferring Project Files to the Raspberry Pi

From your laptop/computer (PowerShell on Windows or Bash on Mac/Linux), copy the `planthead` firmware directory to the Pi:

```bash
# Using scp to copy the folder directly:
scp -r d:/InternMonash/NatureSong/firmware/planthead planthead1@planthead1.local:~/planthead

# Or create a zip file and copy:
# scp planthead.zip planthead1@planthead1.local:~/
```

---

## 4. Installing System Packages & Python Environment

SSH back into your Pi:
```bash
ssh planthead1@planthead1.local
cd ~/planthead
```

### Option A: Automated Setup (Recommended)
Run the automated setup script included in the directory:
```bash
chmod +x setup.sh enable_services.sh
./setup.sh
```
This script automatically:
1. Installs all required `apt` packages (`python3-venv`, `python3-numpy`, `ffmpeg`, `i2c-tools`, `rpicam-apps`, `alsa-utils`, `avahi-daemon`, `comitup`).
2. Creates the Python virtual environment (`venv`) with system packages.
3. Installs all lightweight Python dependencies from `requirements.txt`.
4. Creates necessary data folders (`data/images`, `data/audio`, `data/music`, `logs`, `secrets`).
5. Configures Avahi mDNS discovery (`/etc/avahi/services/planthead.service`).
6. Registers both systemd services (`planthead.service` and `planthead-api.service`).

*(If you ever need to reconfigure or restart only the background services without reinstalling packages, simply run: `./enable_services.sh`)*

---

### Option B: Manual Step-by-Step Installation

If you prefer doing it manually:

1. **Install system packages:**
   ```bash
   sudo apt update
   sudo apt install -y python3-venv python3-pip swig python3-dev liblgpio-dev \
       i2c-tools rpicam-apps alsa-utils ffmpeg avahi-daemon comitup
   ```

2. **Set up Python Virtual Environment:**
   ```bash
   cd ~/planthead
   python3 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Create Required Folders:**
   ```bash
   mkdir -p data/images data/audio data/music logs secrets
   ```

---

## 5. Google Drive Authentication Setup (OAuth Token)

Because the Pi is headless (no browser), Google OAuth tokens must be generated once on a computer with a browser. A ready-to-use tool is included in [`tools/gdrive_auth`](../tools/gdrive_auth).

### Step-by-Step:
1. Open [Google Cloud Console](https://console.cloud.google.com/) -> Create or select your project.
2. Enable the **Google Drive API**.
3. Configure the **OAuth Consent Screen** (User Type: External -> Add your Google account as a **Test User**).
4. Go to **Credentials** -> **Create Credentials** -> **OAuth client ID** -> Select **Desktop App** -> Download the JSON as `credentials.json`.
5. Place `credentials.json` directly into [`tools/gdrive_auth/`](../tools/gdrive_auth/).
6. Run the tool:
   - **On Windows**: Double-click [`tools/gdrive_auth/run_auth.bat`](../tools/gdrive_auth/run_auth.bat) (or run `python tools/gdrive_auth/authorize.py`).
   - **On macOS / Linux**: Run `./tools/gdrive_auth/run_auth.sh` (or `python3 tools/gdrive_auth/authorize.py`).
7. Complete the sign-in in your browser. The tool will:
   - Generate `gdrive_token.json`.
   - **Automatically copy** it directly to [`firmware/planthead/secrets/gdrive_token.json`](planthead/secrets/gdrive_token.json).
8. Now, whenever you transfer `firmware/planthead` to your Raspberry Pi, the token is already in place! *(If the Pi is already running, you can also use `tools/gdrive_auth/copy_to_pi.bat` to send it over via SSH).*

---

## 6. Configuring Environment Variables (`.env`)

On the Pi:
```bash
cd ~/planthead
cp .env.example .env
nano .env
```

Configure the following fields:
```ini
# Unique Device ID: planthead1, planthead2, planthead3, planthead4, planthead5
DEVICE_ID=planthead1

# Adafruit IO Credentials
AIO_USERNAME=your_adafruit_username
AIO_KEY=aio_yourAdafruitIoKeyHere

# Google Drive Target Folder IDs (from your Drive folder URLs)
# https://drive.google.com/drive/folders/<FOLDER_ID>
GDRIVE_IMAGES_FOLDER_ID=1abc..._ImagesFolderID
GDRIVE_AUDIO_FOLDER_ID=1xyz..._AudioFolderID
GDRIVE_MUSIC_FOLDER_ID=1mno..._SharedMusicFolderID

# Local Flask Playback API Port
API_PORT=5000

# Sampling intervals in seconds
SOIL_INTERVAL_SEC=30
CAMERA_INTERVAL_SEC=60
```

---

## 7. Configuring Avahi Service Discovery

Avahi allows the laptop web application to discover each PlantHead unit automatically on the network without hardcoded IP addresses.

Verify that `/etc/avahi/services/planthead.service` contains:
```xml
<?xml version="1.0" standalone='no'?>
<!DOCTYPE service-group SYSTEM "avahi-service.dtd">
<service-group>
  <name replace-wildcards="yes">PlantHead %h</name>
  <service>
    <type>_planthead._tcp</type>
    <port>5000</port>
    <txt-record>device_id=planthead1</txt-record>
  </service>
</service-group>
```
*(Ensure `device_id` matches your `.env` `DEVICE_ID`).*

Restart the service:
```bash
sudo systemctl restart avahi-daemon
```

---

## 8. Relocation & Hotspot Fallback (`comitup`)

When deploying units to different venues or countries, **you do not need to reflash the SD card or connect a monitor/keyboard**.

### How `comitup` Works:
1. In `/etc/comitup.conf`, customize the AP name for each device:
   ```ini
   ap_name: planthead1
   ```
2. Enable and start comitup:
   ```bash
   sudo systemctl enable comitup
   sudo systemctl start comitup
   ```

### Relocating to a New Location / Country:
```
1. Power on the Pi at the new venue.
2. Pi searches for previously known Wi-Fi networks.
3. If no known network is found (after ~1-2 minutes), comitup automatically
   creates a Wi-Fi hotspot named "planthead1" (or "comitup-<id>").
4. On your mobile phone or laptop, connect to the "planthead1" Wi-Fi hotspot.
5. Open your browser and navigate to:
   http://10.42.0.1   (or http://comitup.local)
6. Select the venue's Wi-Fi network from the list and enter its password.
7. Click Connect. The Pi joins the new Wi-Fi, shuts down the hotspot,
   and resumes normal operation.
8. Avahi immediately broadcasts the device on the new network.
```

> [!NOTE]
> Previously saved Wi-Fi networks are preserved! When you bring the Pi back home or to your lab, it will automatically reconnect to your home network without needing any reconfiguration.

---

## 9. Registering and Enabling Systemd Services

Two persistent background services run on each Pi:
- `planthead.service`: Collects soil data (every 30s), takes photos (every 60s), and continuously records ambient audio.
- `planthead-api.service`: Runs the Flask REST API on port 5000 for track listing and remote playback.

### Enabling the services:
```bash
sudo cp ~/planthead/systemd/planthead.service /etc/systemd/system/
sudo cp ~/planthead/systemd/planthead-api.service /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable planthead.service
sudo systemctl enable planthead-api.service

sudo systemctl start planthead.service
sudo systemctl start planthead-api.service
```

### Checking Status and Logs:
```bash
# Check service status
sudo systemctl status planthead.service
sudo systemctl status planthead-api.service

# View live real-time logs
journalctl -u planthead.service -f
journalctl -u planthead-api.service -f
```

---

## 10. Verification & Diagnostics Checklist

Run these quick checks on the Pi to confirm each hardware and software component is working properly:

### 1. Soil Sensor (I2C)
```bash
sudo i2cdetect -y 1
```
*(Verify address `0x36` is present on the grid).*
Test standalone:
```bash
source ~/planthead/venv/bin/activate
python3 -m sensors.soil_sensor
```

### 2. Camera Snapshot
```bash
rpicam-still -o test.jpg
ls -lh test.jpg
```

### 3. Microphone Check
```bash
arecord -l
```
*(Confirm ALSA capture device `card 1, device 0` is listed).*
Test 5-second audio recording:
```bash
arecord -D plughw:0,0 -c 1 -r 44100 -f S32_LE -t wav -d 5 test_mic.wav
```

### 4. Speaker Output Check
```bash
aplay -l
```
Test audio playback:
```bash
source ~/planthead/venv/bin/activate
python3 -m audio.speaker_player
```

### 5. Local Flask API Endpoints
From the Pi (or from your laptop on the same network):
```bash
# Check device status
curl http://localhost:5000/status

# List available music tracks in Google Drive
curl http://localhost:5000/tracks

# Trigger playback
curl -X POST http://localhost:5000/play \
  -H "Content-Type: application/json" \
  -d '{"file_id": "YOUR_DRIVE_FILE_ID", "file_name": "song.mp3"}'

# Stop playback
curl -X POST http://localhost:5000/stop
```

### 6. Avahi Network Discovery Check
From a laptop or another machine with `avahi-utils` installed:
```bash
avahi-browse -r _planthead._tcp
```
The Pi will report its IP address, port `5000`, and `txt-record: device_id=planthead1`.

---

## 11. Multi-Device Deployment Checklist (`planthead1` to `planthead5`)

To deploy units 2 through 5, repeat the exact process with these device-specific values:

| Setting | Unit 1 | Unit 2 | Unit 3 | Unit 4 | Unit 5 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Hostname** | `planthead1` | `planthead2` | `planthead3` | `planthead4` | `planthead5` |
| **Username** | `planthead1` | `planthead2` | `planthead3` | `planthead4` | `planthead5` |
| **`.env` DEVICE_ID** | `planthead1` | `planthead2` | `planthead3` | `planthead4` | `planthead5` |
| **Adafruit IO Soil Feed** | `planthead1-soil-moisture` | `planthead2-soil-moisture` | `planthead3-soil-moisture` | `planthead4-soil-moisture` | `planthead5-soil-moisture` |
| **Avahi TXT Record** | `device_id=planthead1` | `device_id=planthead2` | `device_id=planthead3` | `device_id=planthead4` | `device_id=planthead5` |
| **Comitup AP Name** | `planthead1` | `planthead2` | `planthead3` | `planthead4` | `planthead5` |

All units share the same code, the same Google Drive token (`gdrive_token.json`), and the same shared Google Drive music library folder.

---

## 12. Running the Multi-Device Controller Web App (Laptop)

Once your Raspberry Pis are running on the local network, open the controller dashboard from any laptop (Windows, Mac, or Linux):

1. Navigate to the [`web-app`](../web-app) directory on your laptop.
2. Launch the web app:
   - **On Windows**: Double-click [`web-app/start_web_app.bat`](../web-app/start_web_app.bat)
   - **On macOS / Linux**: Run `./web-app/start.sh`
3. Your browser will automatically open at `http://localhost:8080`.
4. The Zeroconf discovery engine will auto-detect all 5 PlantHead units on your Wi-Fi, display their status, and let you trigger playback directly to each Pi!
