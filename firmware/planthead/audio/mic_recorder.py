"""
Continuous mic recording — no button, no manual trigger.

Records in fixed-length segments (AUDIO_SEGMENT_SEC, default 60s) back
to back, forever. Each segment is saved as its own timestamped WAV
file, then simple audio features (RMS amplitude, onset count) are
extracted and logged to a local CSV, with a summary sent to Adafruit IO.

Recording in segments rather than one huge growing file keeps each
file a manageable size, makes the dataset easy to browse/label later,
and means a crash only loses the current ~60s segment rather than an
entire session's audio.

Run standalone to test just this piece:
    python3 -m audio.mic_recorder
"""
import csv
import logging
import os
import subprocess
import time
from datetime import datetime

import config
from io_client import send
from gdrive_client import upload_file
from audio.audio_features import extract_features

logger = logging.getLogger("planthead.mic_recorder")

CSV_PATH = os.path.join(config.CAMERA_SAVE_DIR.rsplit("/", 1)[0], "audio_log.csv")
# resolves to "data/audio_log.csv"


def init_csv():
    os.makedirs(os.path.dirname(CSV_PATH), exist_ok=True)
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["date", "time", "filename", "duration_sec", "rms", "onset_count"]
            )
        logger.info(f"Created new audio log at {CSV_PATH}")


def log_to_csv(date_str, time_str, filename, duration_sec, rms, onset_count):
    with open(CSV_PATH, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([date_str, time_str, filename, duration_sec, rms, onset_count])


def record_segment():
    """Record one fixed-length segment, block until it's done, return the filepath."""
    os.makedirs(config.AUDIO_SAVE_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(config.AUDIO_SAVE_DIR, f"{timestamp}.wav")

    cmd = [
        "arecord",
        "-D", config.ALSA_DEVICE,
        "-c", str(config.AUDIO_CHANNELS),
        "-r", str(config.AUDIO_SAMPLE_RATE),
        "-f", "S32_LE",
        "-t", "wav",
        "-d", str(config.AUDIO_SEGMENT_SEC),  # fixed duration, arecord exits on its own
        filepath,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"arecord failed: {result.stderr.strip()}")

    return filepath


def process_segment(filepath):
    features = extract_features(filepath)

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")
    filename = os.path.basename(filepath)

    if features:
        log_to_csv(
            date_str, time_str, filename,
            features["duration_sec"], features["rms"], features["onset_count"],
        )
        summary = (
            f"{filename} | {features['duration_sec']}s | "
            f"rms={features['rms']} | onsets={features['onset_count']}"
        )
        logger.info(f"Segment processed: {summary}")
    else:
        log_to_csv(date_str, time_str, filename, config.AUDIO_SEGMENT_SEC, "", "")
        summary = f"{filename} | features unavailable"
        logger.warning(summary)

    send(config.FEED_AUDIO_LOG, summary)
    upload_file(filepath, config.GDRIVE_AUDIO_FOLDER_ID)  # logs its own success/failure


def run_loop():
    init_csv()
    logger.info(
        f"Mic recorder starting — continuous {config.AUDIO_SEGMENT_SEC}s segments"
    )

    while True:
        try:
            filepath = record_segment()
            process_segment(filepath)
        except Exception as e:
            logger.error(f"Recording segment failed: {e}")
            time.sleep(5)  # brief pause before retrying, avoids tight error loop


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_loop()
