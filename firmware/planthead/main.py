"""
Runs all data-collection streams together:
    - soil sensor  (every SOIL_INTERVAL_SEC, -> Adafruit IO + local CSV)
    - camera       (every CAMERA_INTERVAL_SEC, -> Google Drive + local file)
    - mic recorder (push-button triggered, -> local file + Adafruit IO log entry)

Each runs in its own thread so one slow/stuck operation (e.g. a camera
capture that takes a moment) doesn't block the others.

Usage:
    python3 main.py

Stop with Ctrl+C (or, if running as a systemd service:
    sudo systemctl stop planthead.service
).
"""
import logging
from logging.handlers import RotatingFileHandler
import os
import threading

import config
from sensors import soil_sensor
from camera import camera_capture
from audio import mic_recorder


def setup_logging():
    os.makedirs(config.LOG_DIR, exist_ok=True)
    log_file = os.path.join(config.LOG_DIR, "planthead.log")
    file_handler = RotatingFileHandler(log_file, maxBytes=2 * 1024 * 1024, backupCount=1)
    file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers = [file_handler, stream_handler]


def cleanup_temp_dirs():
    """Ensure data/images and data/audio are clean on boot."""
    for folder in [config.CAMERA_SAVE_DIR, config.AUDIO_SAVE_DIR]:
        if os.path.exists(folder):
            for f in os.listdir(folder):
                fp = os.path.join(folder, f)
                try:
                    if os.path.isfile(fp):
                        os.remove(fp)
                except OSError:
                    pass


def main():
    setup_logging()
    cleanup_temp_dirs()
    logger = logging.getLogger("planthead.main")
    logger.info("Starting PlantHead — soil + camera + mic")

    threads = [
        threading.Thread(target=soil_sensor.run_loop, name="soil", daemon=True),
        threading.Thread(target=camera_capture.run_loop, name="camera", daemon=True),
        threading.Thread(target=mic_recorder.run_loop, name="mic", daemon=True),
    ]

    for t in threads:
        t.start()
        logger.info(f"Started thread: {t.name}")

    try:
        while True:
            for t in threads:
                if not t.is_alive():
                    logger.error(f"Thread {t.name} died unexpectedly")
            threading.Event().wait(30)
    except KeyboardInterrupt:
        logger.info("Shutting down (Ctrl+C received)")


if __name__ == "__main__":
    main()
