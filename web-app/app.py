"""
PlantHead Local Web App — Controller & Auto-Discovery Dashboard.
Runs locally on any laptop to discover, monitor, and control PlantHead devices.
"""
import atexit
import logging
import os
import requests
from flask import Flask, jsonify, render_template, request
from dotenv import load_dotenv

from discovery import DiscoveryManager
import gdrive

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("planthead.webapp")

app = Flask(__name__)

# Initialize Zeroconf Discovery
discovery_mgr = DiscoveryManager()
discovery_mgr.start()

atexit.register(discovery_mgr.stop)

PORT = int(os.getenv("WEB_PORT", 8080))


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/devices", methods=["GET"])
def get_devices():
    """Returns list of discovered devices and their live status."""
    devices = discovery_mgr.registry.get_devices()
    return jsonify({
        "count": len(devices),
        "devices": devices,
    })


@app.route("/api/devices/manual", methods=["POST"])
def add_manual_device():
    """Manually add a device by IP/hostname if mDNS is blocked on the network."""
    data = request.get_json(silent=True) or {}
    host = data.get("host")
    port = int(data.get("port", 5000))

    if not host:
        return jsonify({"success": False, "error": "Host or IP required"}), 400

    ok, device_id = discovery_mgr.registry.add_manual_device(host, port)
    if ok:
        return jsonify({
            "success": True,
            "message": f"Successfully connected to {device_id} at {host}:{port}",
            "device_id": device_id,
        })
    else:
        return jsonify({
            "success": False,
            "error": f"Could not reach PlantHead API at http://{host}:{port}/status",
        }), 502


@app.route("/api/tracks", methods=["GET"])
def get_tracks():
    """Returns available music tracks from the shared Google Drive library."""
    devices = discovery_mgr.registry.get_devices()
    tracks = gdrive.get_available_tracks(discovered_devices=devices)
    return jsonify({
        "count": len(tracks),
        "tracks": tracks,
    })


@app.route("/api/play", methods=["POST"])
def play_track():
    """
    Sends playback command to a specific device.
    Payload: {"device_id": "planthead1", "file_id": "...", "file_name": "..."}
    """
    data = request.get_json(silent=True) or {}
    device_id = data.get("device_id")
    file_id = data.get("file_id")
    file_name = data.get("file_name", "unknown")

    if not device_id or not file_id:
        return jsonify({"success": False, "error": "device_id and file_id required"}), 400

    devices = discovery_mgr.registry.get_devices()
    target_dev = next((d for d in devices if d.get("device_id") == device_id), None)

    if not target_dev:
        return jsonify({"success": False, "error": f"Device {device_id} is not online or undiscovered"}), 404

    ip = target_dev.get("ip")
    port = target_dev.get("port", 5000)

    try:
        url = f"http://{ip}:{port}/play"
        res = requests.post(url, json={"file_id": file_id, "file_name": file_name}, timeout=20.0)
        return jsonify(res.json()), res.status_code
    except Exception as e:
        logger.error(f"Failed to send /play command to {device_id} ({ip}:{port}): {e}")
        return jsonify({"success": False, "error": str(e)}), 502


@app.route("/api/stop", methods=["POST"])
def stop_track():
    """
    Sends stop command to a specific device.
    Payload: {"device_id": "planthead1"}
    """
    data = request.get_json(silent=True) or {}
    device_id = data.get("device_id")

    if not device_id:
        return jsonify({"success": False, "error": "device_id required"}), 400

    devices = discovery_mgr.registry.get_devices()
    target_dev = next((d for d in devices if d.get("device_id") == device_id), None)

    if not target_dev:
        return jsonify({"success": False, "error": f"Device {device_id} is not online"}), 404

    ip = target_dev.get("ip")
    port = target_dev.get("port", 5000)

    try:
        url = f"http://{ip}:{port}/stop"
        res = requests.post(url, timeout=5.0)
        return jsonify(res.json()), res.status_code
    except Exception as e:
        logger.error(f"Failed to send /stop command to {device_id} ({ip}:{port}): {e}")
        return jsonify({"success": False, "error": str(e)}), 502


@app.route("/api/stop-all", methods=["POST"])
def stop_all():
    """Stops playback across all discovered devices."""
    devices = discovery_mgr.registry.get_devices()
    results = {}
    for dev in devices:
        d_id = dev.get("device_id")
        ip = dev.get("ip")
        port = dev.get("port", 5000)
        try:
            requests.post(f"http://{ip}:{port}/stop", timeout=3.0)
            results[d_id] = "stopped"
        except Exception:
            results[d_id] = "failed"
    return jsonify({"success": True, "results": results})


if __name__ == "__main__":
    logger.info(f"PlantHead Web App running at http://localhost:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
