#!/usr/bin/env python3
"""
PlantHead Hardware & Cloud Diagnostics Suite.
Tests each peripheral and cloud service individually:
  [1] STEMMA Soil Sensor (I2C)
  [2] Camera Module (CSI)
  [3] INMP441 Microphone (I2S)
  [4] MAX98357A Speaker Amp (I2S)
  [5] Adafruit IO Cloud Telemetry
  [6] Google Drive Cloud Connection

Usage:
  python3 test_hardware.py          (Runs full diagnostic suite)
  python3 test_hardware.py --soil   (Tests only soil sensor)
  python3 test_hardware.py --cam    (Tests only camera)
  python3 test_hardware.py --mic    (Tests only microphone)
  python3 test_hardware.py --spk    (Tests only speaker)
  python3 test_hardware.py --cloud  (Tests Adafruit IO & Google Drive)
"""
import os
import sys
import time
import math
import wave
import struct
import subprocess
import argparse

# Colors for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def header(title):
    print(f"\n{BOLD}{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}{CYAN} >> TEST: {title}{RESET}")
    print(f"{BOLD}{CYAN}{'='*60}{RESET}")


def pass_msg(text):
    print(f"{GREEN}[PASS]{RESET} {text}")


def fail_msg(text, fix=None):
    print(f"{RED}[FAIL]{RESET} {text}")
    if fix:
        print(f"{YELLOW}[HELP]{RESET} {fix}")


# -------------------------------------------------------------------------
# 1. Soil Sensor Test (I2C)
# -------------------------------------------------------------------------
def test_soil_sensor():
    header("STEMMA Soil Sensor (I2C)")
    try:
        import board
        from adafruit_seesaw.seesaw import Seesaw
        import config

        i2c = board.I2C()
        ss = Seesaw(i2c, addr=config.SOIL_SENSOR_ADDR)
        moisture = ss.moisture_read()
        temp = ss.get_temp()

        pass_msg(f"Soil sensor detected at I2C address {hex(config.SOIL_SENSOR_ADDR)}")
        pass_msg(f"Moisture Capacitance : {moisture}")
        pass_msg(f"Soil Temperature     : {temp:.2f} °C")
        return True
    except ImportError as e:
        fail_msg(f"Missing library: {e}", "Run: pip install adafruit-circuitpython-seesaw adafruit-blinka")
        return False
    except Exception as e:
        fail_msg(f"Could not communicate with soil sensor: {e}",
                 "Check wiring: Pin 1 (3.3V), Pin 9 (GND), Pin 3 (SDA), Pin 5 (SCL). Run 'sudo i2cdetect -y 1'")
        return False


# -------------------------------------------------------------------------
# 2. Camera Module Test (CSI)
# -------------------------------------------------------------------------
def test_camera():
    header("Camera Module (CSI Ribbon)")
    test_img = "/tmp/planthead_test_camera.jpg"
    if os.path.exists(test_img):
        os.remove(test_img)

    # Check for rpicam-still or libcamera-still
    cam_cmd = "rpicam-still" if subprocess.run(["which", "rpicam-still"], capture_output=True).returncode == 0 else "libcamera-still"

    cmd = [cam_cmd, "-o", test_img, "--width", "1280", "--height", "720", "--timeout", "1000", "--nopreview"]
    print(f"Executing: {' '.join(cmd)} ...")

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0 and os.path.exists(test_img) and os.path.getsize(test_img) > 1000:
        size_kb = os.path.getsize(test_img) / 1024
        pass_msg(f"Snapshot captured successfully! File size: {size_kb:.1f} KB at {test_img}")
        return True
    else:
        err = result.stderr.strip() or "No image file created"
        fail_msg(f"Camera capture failed: {err}",
                 "Check CSI ribbon cable orientation (blue tape faces away from board on Pi Zero). Run 'rpicam-hello'")
        return False


# -------------------------------------------------------------------------
# 3. Microphone Test (I2S INMP441)
# -------------------------------------------------------------------------
def test_microphone():
    header("INMP441 Microphone (I2S Recording)")
    test_wav = "/tmp/planthead_test_mic.wav"
    if os.path.exists(test_wav):
        os.remove(test_wav)

    import config

    # Check ALSA device
    alsa_check = subprocess.run(["arecord", "-l"], capture_output=True, text=True)
    if "card" not in alsa_check.stdout:
        fail_msg("No ALSA capture devices found!",
                 "Ensure 'dtoverlay=googlevoicehat-soundcard' is in /boot/firmware/config.txt and you rebooted.")
        return False

    print(f"Recording 3-second audio sample using {config.ALSA_DEVICE} ...")
    cmd = [
        "arecord", "-D", config.ALSA_DEVICE,
        "-c", "1", "-r", "44100", "-f", "S32_LE",
        "-t", "wav", "-d", "3", test_wav
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)

    if res.returncode == 0 and os.path.exists(test_wav) and os.path.getsize(test_wav) > 1000:
        # Calculate volume
        try:
            from audio.audio_features import extract_features
            feats = extract_features(test_wav)
            rms = feats["rms"] if feats else 0.0
            pass_msg(f"Microphone recorded 3s audio! RMS Volume: {rms} ({test_wav})")
        except Exception:
            pass_msg(f"Microphone recorded successfully to {test_wav}")
        return True
    else:
        fail_msg(f"arecord failed: {res.stderr.strip()}",
                 f"Check wiring: SCK->Pin12, WS->Pin35, SD->Pin38, VDD->Pin17, GND->Pin14, L/R->GND. Also verify ALSA device in config.py.")
        return False


# -------------------------------------------------------------------------
# 4. Speaker Test (I2S MAX98357A Amp)
# -------------------------------------------------------------------------
def test_speaker():
    header("MAX98357A Speaker Amp (I2S Audio Output)")
    test_wav = "/tmp/planthead_test_beep.wav"

    # Generate a pure 440Hz sine tone (1.5 seconds) using standard library
    sample_rate = 44100
    duration = 1.5
    freq = 440.0
    n_samples = int(sample_rate * duration)

    with wave.open(test_wav, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        for i in range(n_samples):
            value = int(math.sin(2 * math.pi * freq * (i / sample_rate)) * 16000)
            data = struct.pack("<h", value)
            wf.writeframes(data)

    import config
    print(f"Playing 440Hz test tone on {config.SPEAKER_ALSA_DEVICE} ...")
    cmd = ["aplay", "-D", config.SPEAKER_ALSA_DEVICE, test_wav]
    res = subprocess.run(cmd, capture_output=True, text=True)

    if res.returncode == 0:
        pass_msg("Audio played to ALSA device without errors!")
        print(f"{YELLOW}>> Did you hear a 1.5-second beep from your speaker? (If no, check amp 5V/GND and speaker wire terminals).{RESET}")
        return True
    else:
        fail_msg(f"aplay failed: {res.stderr.strip()}",
                 "Check amp wiring: BCLK->Pin12, LRC->Pin35, DIN->Pin40, VIN->5V, GND->GND.")
        return False


# -------------------------------------------------------------------------
# 5. Adafruit IO Cloud Test
# -------------------------------------------------------------------------
def test_adafruit_io():
    header("Adafruit IO Cloud Telemetry")
    import config
    if not config.AIO_USERNAME or not config.AIO_KEY:
        fail_msg("AIO_USERNAME or AIO_KEY is missing in your .env file!", "Edit .env with your credentials.")
        return False

    try:
        from Adafruit_IO import Client
        aio = Client(config.AIO_USERNAME, config.AIO_KEY)
        feeds = aio.feeds()
        pass_msg(f"Successfully authenticated with Adafruit IO as user '{config.AIO_USERNAME}'")
        pass_msg(f"Account has {len(feeds)} active feeds.")
        return True
    except Exception as e:
        fail_msg(f"Adafruit IO connection failed: {e}", "Check your AIO_USERNAME and AIO_KEY in .env")
        return False


# -------------------------------------------------------------------------
# 6. Google Drive Cloud Test
# -------------------------------------------------------------------------
def test_google_drive():
    header("Google Drive Cloud API & Token")
    token_file = "secrets/gdrive_token.json"
    if not os.path.exists(token_file):
        fail_msg(f"Token file '{token_file}' not found!",
                 "Generate it on your laptop using tools/gdrive_auth/run_auth.bat and copy it to secrets/gdrive_token.json.")
        return False

    try:
        import gdrive_client
        service = gdrive_client.get_service()
        about = service.about().get(fields="user(displayName, emailAddress)").execute()
        user_info = about.get("user", {})
        pass_msg(f"Google Drive authenticated as: {user_info.get('displayName')} ({user_info.get('emailAddress')})")

        # Test listing music tracks
        tracks = gdrive_client.list_music_tracks()
        pass_msg(f"Google Drive music library found {len(tracks)} tracks.")
        return True
    except Exception as e:
        fail_msg(f"Google Drive API test failed: {e}",
                 "Regenerate your token using tools/gdrive_auth/run_auth.bat and recopy to secrets/.")
        return False


# -------------------------------------------------------------------------
# Main Execution
# -------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="PlantHead Diagnostics")
    parser.add_argument("--soil", action="store_true", help="Test Soil Sensor")
    parser.add_argument("--cam", action="store_true", help="Test Camera")
    parser.add_argument("--mic", action="store_true", help="Test Microphone")
    parser.add_argument("--spk", action="store_true", help="Test Speaker")
    parser.add_argument("--cloud", action="store_true", help="Test Adafruit IO & Google Drive")
    args = parser.parse_args()

    print(f"\n{BOLD}PlantHead Comprehensive Diagnostic Utility{RESET}")
    print(f"Working Directory: {os.getcwd()}\n")

    single_test = any([args.soil, args.cam, args.mic, args.spk, args.cloud])

    results = {}
    if args.soil or not single_test:
        results["Soil Sensor"] = test_soil_sensor()
    if args.cam or not single_test:
        results["Camera Module"] = test_camera()
    if args.mic or not single_test:
        results["Microphone"] = test_microphone()
    if args.spk or not single_test:
        results["Speaker Amp"] = test_speaker()
    if args.cloud or not single_test:
        results["Adafruit IO"] = test_adafruit_io()
        results["Google Drive"] = test_google_drive()

    print(f"\n{BOLD}{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}DIAGNOSTIC SUMMARY:{RESET}")
    for name, ok in results.items():
        status = f"{GREEN}PASS{RESET}" if ok else f"{RED}FAIL{RESET}"
        print(f"  - {name:<25} : {status}")
    print(f"{BOLD}{CYAN}{'='*60}{RESET}\n")


if __name__ == "__main__":
    main()
