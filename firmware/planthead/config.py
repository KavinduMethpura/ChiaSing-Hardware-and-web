"""
Central configuration for the PlantHead project.
Secrets (Adafruit IO username/key, Drive folder IDs, DEVICE_ID) live in .env, loaded here.
Hardware pins, intervals, and default device configurations are managed here.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# --- Device Identity (unique per Raspberry Pi: planthead1 .. planthead5) ---
DEVICE_ID = os.getenv("DEVICE_ID", "planthead1")

# --- Adafruit IO credentials (from .env) ---
AIO_USERNAME = os.getenv("AIO_USERNAME")
AIO_KEY = os.getenv("AIO_KEY")

# --- Feed names (grouped per device in Adafruit IO) ---
# Matches Adafruit IO group format: <group_key>.<feed_key>
# Example: planthead1.planthead1-soil-moisture, planthead1.planthead1-soil-temp, planthead1.planthead1-audio-log
FEED_SOIL_MOISTURE = os.getenv("FEED_SOIL_MOISTURE", f"{DEVICE_ID}.{DEVICE_ID}-soil-moisture")
FEED_SOIL_TEMP = os.getenv("FEED_SOIL_TEMP", f"{DEVICE_ID}.{DEVICE_ID}-soil-temp")
FEED_AUDIO_LOG = os.getenv("FEED_AUDIO_LOG", f"{DEVICE_ID}.{DEVICE_ID}-audio-log")

# --- Telemetry & Sampling Intervals ---
# Soil moisture sampling interval (seconds). 30s is optimal for Adafruit IO rate limits.
SOIL_INTERVAL_SEC = int(os.getenv("SOIL_INTERVAL_SEC", "30"))
CAMERA_INTERVAL_SEC = int(os.getenv("CAMERA_INTERVAL_SEC", "60"))  # 1 minute

# --- Soil sensor (I2C) ---
SOIL_SENSOR_ADDR = 0x36  # default I2C address for Adafruit STEMMA soil sensor

# --- Camera ---
CAMERA_WIDTH = 1920
CAMERA_HEIGHT = 1080
CAMERA_SAVE_DIR = "data/images"

# --- Google Drive upload & playback ---
# Folder IDs from Google Drive URLs
GDRIVE_IMAGES_FOLDER_ID = os.getenv("GDRIVE_IMAGES_FOLDER_ID", "")
GDRIVE_AUDIO_FOLDER_ID = os.getenv("GDRIVE_AUDIO_FOLDER_ID", "")
GDRIVE_MUSIC_FOLDER_ID = os.getenv("GDRIVE_MUSIC_FOLDER_ID", "")

# --- Audio Recording (Sound-Activated / Silence Detection) ---
AUDIO_SAVE_DIR = "data/audio"
AUDIO_SEGMENT_SEC = 60      # length of each recorded WAV segment, in seconds
AUDIO_SAMPLE_RATE = 44100
AUDIO_CHANNELS = 1
# Minimum RMS volume to upload. If room is quiet (RMS < threshold), file is discarded.
# Set to 0.0 to disable silence filtering and upload all ambient silence.
AUDIO_RMS_THRESHOLD = float(os.getenv("AUDIO_RMS_THRESHOLD", "0.0001"))
ALSA_DEVICE = os.getenv("ALSA_DEVICE", "plughw:0,0")  # card 0 on Pi Zero Lite

# --- Speaker Output (MAX98357A mono amp) & Music Playback ---
SPEAKER_ALSA_DEVICE = os.getenv("SPEAKER_ALSA_DEVICE", "plughw:0,0")  # card 0 on Pi Zero Lite
SPEAKER_TEST_FILE = "audio/test_sounds/test.wav"
MUSIC_SAVE_DIR = "data/music"       # local cache directory for downloaded music tracks

# --- Local Flask Playback API ---
API_HOST = "0.0.0.0"
API_PORT = int(os.getenv("API_PORT", "5000"))

# --- Logging ---
LOG_DIR = "logs"
