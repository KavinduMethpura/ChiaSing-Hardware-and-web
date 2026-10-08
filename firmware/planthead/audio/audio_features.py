"""
Computes lightweight audio features from a recorded WAV file:
    - RMS (root-mean-square) amplitude — a measure of overall loudness
    - Duration in seconds

Uses built-in Python `wave` module and numpy (lightweight, no librosa/numba/llvmlite dependency).
Runs in milliseconds on Raspberry Pi Zero W without eating CPU cycles.
"""
import logging
import math
import wave
import numpy as np

logger = logging.getLogger("planthead.audio_features")


def extract_features(filepath):
    """
    Returns a dict: {rms, duration_sec, onset_count}
    Returns None if the file can't be read/analyzed.
    """
    try:
        with wave.open(filepath, "rb") as wf:
            framerate = wf.getframerate()
            n_frames = wf.getnframes()
            sample_width = wf.getsampwidth()
            duration_sec = n_frames / float(framerate) if framerate > 0 else 0.0

            raw_bytes = wf.readframes(n_frames)

            # S32_LE (32-bit audio from arecord)
            if sample_width == 4:
                dtype = np.int32
            elif sample_width == 2:
                dtype = np.int16
            else:
                dtype = np.uint8

            if len(raw_bytes) > 0:
                samples = np.frombuffer(raw_bytes, dtype=dtype)
                max_val = float(np.iinfo(dtype).max)
                norm_samples = samples.astype(np.float32) / max_val
                rms = float(np.sqrt(np.mean(norm_samples ** 2)))
            else:
                rms = 0.0

        return {
            "rms": round(rms, 5),
            "duration_sec": round(duration_sec, 2),
            "onset_count": 0,
        }
    except Exception as e:
        logger.error(f"Feature extraction failed for {filepath}: {e}")
        return None
