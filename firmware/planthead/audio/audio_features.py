"""
Computes simple audio features from a recorded WAV file:
    - RMS (root-mean-square) amplitude — a measure of overall loudness
    - Onset count — how many distinct sound events/attacks occurred
      (e.g. separate chirps, claps, spoken syllables)

Called from mic_recorder.py right after a recording stops, so features
land in the log alongside the raw file — no need to re-open files later.
"""
import logging

import numpy as np
import librosa

logger = logging.getLogger("planthead.audio_features")


def extract_features(filepath):
    """
    Returns a dict: {rms, duration_sec, onset_count}
    Returns None if the file can't be read/analyzed.
    """
    try:
        y, sr = librosa.load(filepath, sr=None, mono=True)

        rms = float(np.sqrt(np.mean(y ** 2)))
        duration_sec = len(y) / sr

        onset_frames = librosa.onset.onset_detect(y=y, sr=sr)
        onset_count = len(onset_frames)

        return {
            "rms": round(rms, 5),
            "duration_sec": round(duration_sec, 2),
            "onset_count": onset_count,
        }
    except Exception as e:
        logger.error(f"Feature extraction failed for {filepath}: {e}")
        return None
