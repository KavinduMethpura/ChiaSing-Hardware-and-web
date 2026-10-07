# Implementation Plan - NatureSong Hardware Wiring & Adafruit IO Telemetry System

This document provides a comprehensive guide and software plan for connecting the hardware peripherals (PowerBoost 1000C battery power, STEMMA Soil Sensor, Pi Camera Module, INMP441 I2S Microphone) to the **Raspberry Pi Zero 2 W**, and setting up Python scripts to log data to **Adafruit IO**.

---

## Hardware Wiring Architecture

### 1. Power Supply Wiring (PowerBoost 1000C + 1100mAh LiPo)
- **LiPo Battery (1100mAh)**: Plug the JST-PH 2-pin connector into the **JST** port on the PowerBoost 1000C.
- **PowerBoost 1000C to Pi Zero 2 W**:
  - Connect PowerBoost `5V` (or USB-A out) to Pi Zero 2 W `5V` (Pin 2 or Pin 4).
  - Connect PowerBoost `GND` to Pi Zero 2 W `GND` (Pin 6).
- **Charging**: Plug a Micro-USB cable into the PowerBoost 1000C to charge the LiPo battery while running the Pi.

```
[ 1100mAh LiPo ] ---> [ JST Port on PowerBoost 1000C ] 
                          ├── 5V  ---> Pi Zero 2 W Pin 2 (5V)
                          └── GND ---> Pi Zero 2 W Pin 6 (GND)
```

---

### 2. GPIO Pinout Mapping Matrix

The Raspberry Pi Zero 2 W 40-pin GPIO header is mapped as follows to avoid pin conflicts between I2C (soil sensor) and I2S (microphone & future audio amp):

| Peripheral Component | Pin Name / Function | Pi Zero 2 W Physical Pin | Pi Header Label / BCM |
| :--- | :--- | :--- | :--- |
| **Adafruit STEMMA Soil Sensor (I2C)** | VIN | Pin 1 | 3.3V Power |
| | GND | Pin 9 | Ground |
| | SDA | Pin 3 | GPIO 2 (I2C1 SDA) |
| | SCL | Pin 5 | GPIO 3 (I2C1 SCL) |
| **INMP441 MEMS Microphone (I2S)** | VDD | Pin 17 | 3.3V Power |
| | GND | Pin 14 | Ground |
| | L/R (Channel select) | Pin 20 (or connect to GND) | Ground (Left Channel) |
| | SD (Serial Data) | Pin 38 | GPIO 20 (PCM_DIN) |
| | SCK (Bit Clock) | Pin 12 | GPIO 18 (PCM_CLK) |
| | WS (Word Select / LRCLK) | Pin 35 | GPIO 19 (PCM_FS) |
| **Pi Camera Module** | 22-pin FPC Ribbon | CSI Connector Port | Dedicated CSI Interface |

> [!NOTE]
> When you later add the MAX98357A I2S Audio Amp, it will share the **BCLK (Pin 12)** and **LRCLK/WS (Pin 35)** with the microphone, but its **DIN (Data In)** will connect to **Pin 40 (GPIO 21 / PCM_DOUT)**.

---

## Raspberry Pi OS Configuration Requirements

SSH into your Pi Zero 2 W and run the following configuration setup:

### 1. Enable Interfaces (`/boot/firmware/config.txt` or `raspi-config`)
1. **Enable I2C & I2S**:
   ```bash
   sudo raspi-config
   ```
   - Go to `Interface Options` -> `I2C` -> `Enable`
   - Exit and reboot: `sudo reboot`

2. **Configure I2S Microphone Driver**:
   Add the I2S microphone device tree overlay to `/boot/firmware/config.txt` (or `/boot/config.txt` on older OS):
   ```ini
   # Enable I2S sound card overlay for INMP441
   dtoverlay=googlevoicehat-soundcard
   ```
   *Alternatively, `dtoverlay=i2s-mmap` or standard I2S mic module driver can be loaded.*

3. **Install System Dependencies**:
   ```bash
   sudo apt update
   sudo apt install -y i2c-tools python3-pip python3-numpy libcamera-apps python3-picamera2 portaudio19-dev
   ```

---

## Proposed Software Architecture

We will create a structured firmware codebase inside `d:\InternMonash\NatureSong\firmware`:

```
d:\InternMonash\NatureSong\firmware/
├── config.py             # Adafruit IO credentials & sampling intervals
├── sensors/
│   ├── __init__.py
│   ├── soil.py           # Adafruit Seesaw STEMMA Soil driver & reader
│   ├── sound.py          # INMP441 I2S microphone reader (RMS & sound level calculation)
│   └── camera.py         # Pi Camera image capture & base64 encoding
├── main.py               # Main daemon logging data & pushing to Adafruit IO
├── requirements.txt      # Python dependencies
└── README.md             # Setup and running instructions
```

### File Breakdown

#### 1. `config.py` [NEW]
Contains Adafruit IO credentials (`AIO_USERNAME`, `AIO_KEY`), feed keys (`soil-moisture`, `soil-temperature`, `sound-level`, `camera-image`), and logging interval settings.

#### 2. `sensors/soil.py` [NEW]
Handles I2C communication with Adafruit Seesaw Soil Sensor (Address `0x36`). Returns moisture raw capacitance and temperature in °C.

#### 3. `sensors/sound.py` [NEW]
Captures audio chunks via I2S ALSA / PyAudio stream, calculates Root Mean Square (RMS) amplitude and dB SPL estimation.

#### 4. `sensors/camera.py` [NEW]
Captures snapshot photos using `picamera2` / `rpicam-still`, resizes for web optimization, and encodes as base64 string for Adafruit IO Image feed.

#### 5. `main.py` [NEW]
Main event loop using `adafruit-io` MQTT / REST client to push telemetry readings every 60 seconds (or configured interval).

---

## User Review Required

> [!IMPORTANT]
> **Adafruit IO Account**: Do you already have an Adafruit IO account and API key? You will need your `AIO_USERNAME` and `AIO_KEY` to test data transmission to the cloud dashboard.
>
> **Pi Camera Ribbon Cable**: Ensure you are using the specific narrow Raspberry Pi Zero CSI ribbon cable (15-pin 1.0mm pitch to 22-pin 0.5mm pitch), as the standard Pi 4 ribbon cable is too wide for the Pi Zero 2 W connector.

---

## Verification Plan

### Manual & Hardware Verification
1. **I2C Bus Detection**:
   ```bash
   sudo i2cdetect -y 1
   ```
   Verify `0x36` appears on the bus grid.
2. **Audio Input Detection**:
   ```bash
   arecord -l
   ```
   Confirm I2S capture device is listed.
3. **Camera Test**:
   ```bash
   rpicam-still -o test.jpg
   ```
   Verify image file is captured cleanly.
4. **Adafruit IO Live Data Feed Verification**:
   Run `python3 main.py` and inspect live readings appearing on the Adafruit IO dashboard.
