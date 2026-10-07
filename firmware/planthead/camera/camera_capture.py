"""
Captures a still image every CAMERA_INTERVAL_SEC via rpicam-still,
saves it locally, and uploads the full-resolution file to Google Drive.

No size limit issue here (unlike Adafruit IO) — full 640x480 (or higher)
JPEGs upload as-is. See README for Google Drive service account setup.

Run standalone to test just this piece:
    python3 -m camera.camera_capture
"""
import logging
import os
import subprocess
import time
from datetime import datetime

import config
from gdrive_client import upload_file

logger = logging.getLogger("planthead.camera")


def capture_image():
    """Capture a still via rpicam-still, return the local file path."""
    os.makedirs(config.CAMERA_SAVE_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(config.CAMERA_SAVE_DIR, f"{timestamp}.jpg")

    cmd = [
        "rpicam-still",
        "-o", filepath,
        "--width", str(config.CAMERA_WIDTH),
        "--height", str(config.CAMERA_HEIGHT),
        "--timeout", "1000",   # ms — brief warm-up before capture
        "--nopreview",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"rpicam-still failed: {result.stderr.strip()}")

    return filepath


def run_loop():
    logger.info("Camera capture loop starting")
    while True:
        try:
            filepath = capture_image()
            size_kb = os.path.getsize(filepath) / 1024
            logger.info(f"Captured {filepath} ({size_kb:.1f} KB)")

            upload_file(filepath, config.GDRIVE_IMAGES_FOLDER_ID)  # logs its own success/failure internally

        except Exception as e:
            logger.error(f"Camera capture failed: {e}")

        time.sleep(config.CAMERA_INTERVAL_SEC)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_loop()

