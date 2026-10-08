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

    rms = features.get("rms", 0.0) if features else 0.0
    duration_sec = features.get("duration_sec", config.AUDIO_SEGMENT_SEC) if features else config.AUDIO_SEGMENT_SEC
    onset_count = features.get("onset_count", 0) if features else 0

    # Silence Detection Filter:
    # If the environment is calm/quiet (RMS below threshold), discard the file
    # to conserve local SD card storage and avoid uploading silent clips to Drive.
    if config.AUDIO_RMS_THRESHOLD > 0 and rms < config.AUDIO_RMS_THRESHOLD:
        logger.info(
            f"Segment {filename} was calm/silent (RMS: {rms:.5f} < threshold {config.AUDIO_RMS_THRESHOLD}). "
            f"Discarded file to conserve storage."
        )
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except OSError:
                pass
        return

    # Sound Event Detected! Log summary to Adafruit IO and upload audio to Google Drive
    summary = f"{filename} | {duration_sec}s | rms={rms} | SOUND DETECTED"
    logger.info(f"Sound event captured: {summary}")

    try:
        send(config.FEED_AUDIO_LOG, summary)
        upload_file(filepath, config.GDRIVE_AUDIO_FOLDER_ID)
    except Exception as e:
        logger.error(f"Failed to upload sound event: {e}")
    finally:
        # Auto-delete local audio file immediately after upload to prevent SD card fill-up
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
                logger.debug(f"Removed local temp audio {filepath}")
            except OSError as e:
                logger.warning(f"Failed to remove temp audio: {e}")


def run_loop():
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
