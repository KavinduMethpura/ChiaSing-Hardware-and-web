"""
Plays audio files out through the MAX98357A I2S amp + speaker.

Supports:
  - Direct synchronous playback: play_file(filepath)
  - Asynchronous background playback with state tracking: play_file_async(filepath, track_info)
  - Instant interruption / stop: stop_playback()
  - Playback status inspection: get_playback_status()
  - Auto MP3 conversion to WAV on-the-fly via ffmpeg
"""
import logging
import os
import subprocess
import sys
import tempfile
import threading
import time

import config

logger = logging.getLogger("planthead.speaker_player")

_lock = threading.Lock()
_current_process = None
_current_thread = None
_current_temp_file = None
_current_track_info = None
_playback_state = "idle"  # "idle", "playing", "stopped", "error"
_started_at = None


def _convert_mp3_to_wav(mp3_path):
    """Convert an MP3 to a temp WAV file using ffmpeg, return the WAV path."""
    tmp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp_wav.close()

    cmd = [
        "ffmpeg", "-y", "-i", mp3_path,
        "-ar", str(config.AUDIO_SAMPLE_RATE),
        "-ac", "1",  # mono mixdown
        tmp_wav.name,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        if os.path.exists(tmp_wav.name):
            os.remove(tmp_wav.name)
        raise RuntimeError(f"ffmpeg conversion failed: {result.stderr.strip()}")

    return tmp_wav.name


def stop_playback():
    """Immediately stop any active audio playback."""
    global _current_process, _current_temp_file, _playback_state, _current_track_info, _started_at
    with _lock:
        if _current_process and _current_process.poll() is None:
            logger.info("Stopping active playback process...")
            try:
                _current_process.terminate()
                _current_process.wait(timeout=1.0)
            except Exception:
                try:
                    _current_process.kill()
                except Exception:
                    pass

        if _current_temp_file and os.path.exists(_current_temp_file):
            try:
                os.remove(_current_temp_file)
            except OSError:
                pass
            _current_temp_file = None

        _current_process = None
        _playback_state = "stopped"
        _current_track_info = None
        _started_at = None
        logger.info("Audio playback stopped")
        return True


def get_playback_status():
    """
    Returns current playback status dictionary:
    {
        'state': 'playing' | 'idle' | 'stopped',
        'track': {'id': ..., 'name': ...} | None,
        'started_at': float | None,
        'elapsed_sec': float | None
    }
    """
    global _playback_state, _current_track_info, _started_at, _current_process
    with _lock:
        if _playback_state == "playing":
            if _current_process and _current_process.poll() is not None:
                # Process has completed
                _playback_state = "idle"
                _current_track_info = None
                _started_at = None

        elapsed = round(time.time() - _started_at, 1) if (_started_at and _playback_state == "playing") else None

        return {
            "state": _playback_state,
            "track": _current_track_info,
            "started_at": _started_at,
            "elapsed_sec": elapsed,
        }


def _playback_worker(filepath, track_info):
    global _current_process, _current_temp_file, _playback_state, _started_at, _current_track_info

    wav_path = filepath
    cleanup_temp = False

    try:
        if filepath.lower().endswith(".mp3"):
            logger.info(f"Converting {filepath} to mono WAV for playback...")
            wav_path = _convert_mp3_to_wav(filepath)
            cleanup_temp = True
            with _lock:
                _current_temp_file = wav_path

        cmd = ["aplay", "-D", config.SPEAKER_ALSA_DEVICE, wav_path]
        logger.info(f"Playing {filepath} on {config.SPEAKER_ALSA_DEVICE}...")

        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        with _lock:
            _current_process = proc
            _playback_state = "playing"
            _started_at = time.time()
            _current_track_info = track_info or {"name": os.path.basename(filepath)}

        _, stderr = proc.communicate()

        if proc.returncode != 0 and _playback_state == "playing":
            err_msg = stderr.decode().strip() if stderr else "Unknown aplay error"
            logger.error(f"aplay exited with error: {err_msg}")
            with _lock:
                _playback_state = "error"
        else:
            with _lock:
                if _playback_state == "playing":
                    _playback_state = "idle"
                    _current_track_info = None
                    _started_at = None

    except Exception as e:
        logger.error(f"Playback worker error for {filepath}: {e}")
        with _lock:
            _playback_state = "error"
    finally:
        if cleanup_temp and os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except OSError:
                pass
            with _lock:
                _current_temp_file = None


def play_file_async(filepath, track_info=None):
    """
    Start playing an audio file in a background thread.
    Stops any currently playing audio first.
    Returns True if started, False if file doesn't exist.
    """
    if not os.path.exists(filepath):
        logger.error(f"Cannot play non-existent file: {filepath}")
        return False

    stop_playback()

    thread = threading.Thread(
        target=_playback_worker,
        args=(filepath, track_info),
        name="speaker_playback",
        daemon=True,
    )
    thread.start()
    return True


def play_file(filepath):
    """
    Synchronous blocking playback (for manual command-line testing).
    """
    play_file_async(filepath)
    # Block until finished
    while True:
        status = get_playback_status()
        if status["state"] != "playing":
            break
        time.sleep(0.5)
    return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    target = sys.argv[1] if len(sys.argv) > 1 else config.SPEAKER_TEST_FILE

    if not os.path.exists(target):
        print(f"\nNo file at '{target}'.")
        print("Provide an audio file to test:")
        print("    python3 -m audio.speaker_player /path/to/test.wav\n")
        sys.exit(1)

    print(f"Playing {target} (blocking)...")
    play_file(target)
