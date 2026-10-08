"""
Local Flask API for PlantHead Device Playback & Status.

Runs on each Raspberry Pi (e.g., port 5000), allowing the laptop-based discovery web app
or collaborators to control playback and inspect device state over the local network.

Endpoints:
  GET  /status  - Device health, current playback state, and feed IDs
  GET  /tracks  - List available music tracks in the shared Google Drive folder
  POST /play    - Play a specific Drive track: {"file_id": "...", "file_name": "..."}
  POST /stop    - Immediately stop current audio playback
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from flask import Flask, jsonify, request
from flask_cors import CORS

import config
import gdrive_client
from audio import speaker_player

# Set up logging with rotating file handler (max 2MB)
os.makedirs(config.LOG_DIR, exist_ok=True)
api_log_file = os.path.join(config.LOG_DIR, "planthead_api.log")
api_handler = RotatingFileHandler(api_log_file, maxBytes=2 * 1024 * 1024, backupCount=1)
api_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))

logger = logging.getLogger("planthead.api")
logger.setLevel(logging.INFO)
logger.handlers = [api_handler, stream_handler]

app = Flask(__name__)
CORS(app)  # Enable Cross-Origin requests from the laptop web app


@app.route("/status", methods=["GET"])
def get_status():
    """Return device ID, playback status, and feed configurations."""
    playback = speaker_player.get_playback_status()
    return jsonify({
        "device_id": config.DEVICE_ID,
        "status": "online",
        "playback": playback,
        "feeds": {
            "soil_moisture": config.FEED_SOIL_MOISTURE,
            "soil_temp": config.FEED_SOIL_TEMP,
            "audio_log": config.FEED_AUDIO_LOG,
        },
        "version": "1.0.0",
    }), 200


@app.route("/tracks", methods=["GET"])
def get_tracks():
    """List available audio files in Google Drive music folder."""
    tracks = gdrive_client.list_music_tracks()
    return jsonify({
        "device_id": config.DEVICE_ID,
        "count": len(tracks),
        "tracks": tracks,
    }), 200


@app.route("/play", methods=["POST"])
def play_track():
    """
    Download (if not cached) and play the requested track.
    Expected JSON payload:
      {"file_id": "1A2B3C...", "file_name": "track1.mp3"}
    """
    data = request.get_json(silent=True) or {}
    file_id = data.get("file_id")
    file_name = data.get("file_name", "unknown_track")

    if not file_id:
        return jsonify({"success": False, "error": "Missing 'file_id' parameter"}), 400

    logger.info(f"Received playback request for file_id: {file_id} ({file_name})")

    # Download from Google Drive (or retrieve from local cache)
    local_path = gdrive_client.download_file(file_id)
    if not local_path or not os.path.exists(local_path):
        return jsonify({
            "success": False,
            "error": f"Failed to download or locate file {file_id} from Google Drive",
        }), 502

    # Start playback asynchronously
    started = speaker_player.play_file_async(
        local_path,
        track_info={"id": file_id, "name": file_name, "path": local_path},
    )

    if started:
        return jsonify({
            "success": True,
            "message": f"Playback started for {file_name}",
            "device_id": config.DEVICE_ID,
            "track": {"id": file_id, "name": file_name},
        }), 200
    else:
        return jsonify({
            "success": False,
            "error": "Failed to trigger playback",
        }), 500


@app.route("/stop", methods=["POST"])
def stop_track():
    """Immediately stop audio playback."""
    speaker_player.stop_playback()
    return jsonify({
        "success": True,
        "message": "Playback stopped",
        "device_id": config.DEVICE_ID,
    }), 200


if __name__ == "__main__":
    logger.info(f"Starting PlantHead API for {config.DEVICE_ID} on {config.API_HOST}:{config.API_PORT}")
    app.run(host=config.API_HOST, port=config.API_PORT, debug=False)
