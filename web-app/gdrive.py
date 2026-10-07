"""
Google Drive Music Library Fetcher for Web App.
Fetches tracks either directly via Google Drive API (if local token exists),
or proxies through one of the active PlantHead devices.
"""
import logging
import os
import requests
from dotenv import load_dotenv

logger = logging.getLogger("planthead.web_gdrive")

# Search for gdrive_token.json in standard repo locations
TOKEN_SEARCH_PATHS = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "tools", "gdrive_auth", "gdrive_token.json")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "firmware", "planthead", "secrets", "gdrive_token.json")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "secrets", "gdrive_token.json")),
]

# Search for .env to get GDRIVE_MUSIC_FOLDER_ID
ENV_SEARCH_PATHS = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), ".env")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "firmware", "planthead", ".env")),
]

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.readonly",
]

_cached_tracks = []


def find_token_path():
    for p in TOKEN_SEARCH_PATHS:
        if os.path.exists(p):
            return p
    return None


def get_music_folder_id():
    for p in ENV_SEARCH_PATHS:
        if os.path.exists(p):
            load_dotenv(p)
            folder_id = os.getenv("GDRIVE_MUSIC_FOLDER_ID")
            if folder_id and folder_id != "your_shared_music_folder_id_here":
                return folder_id
    return os.getenv("GDRIVE_MUSIC_FOLDER_ID", "")


def list_tracks_direct():
    """Attempt direct Google Drive API query using laptop credentials."""
    token_path = find_token_path()
    folder_id = get_music_folder_id()

    if not token_path or not folder_id:
        return None

    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(token_path, "w") as f:
                    f.write(creds.to_json())
            else:
                return None

        service = build("drive", "v3", credentials=creds)
        query = f"'{folder_id}' in parents and trashed = false"
        results = service.files().list(
            q=query,
            pageSize=100,
            fields="files(id, name, mimeType, size)",
            orderBy="name",
        ).execute()

        files = results.get("files", [])
        logger.info(f"Retrieved {len(files)} tracks directly from Google Drive")
        return files
    except Exception as e:
        logger.warning(f"Direct Google Drive query failed: {e}")
        return None


def list_tracks_via_device(device_ip, device_port=5000):
    """Proxy track listing through an active PlantHead device."""
    try:
        url = f"http://{device_ip}:{device_port}/tracks"
        res = requests.get(url, timeout=3.5)
        if res.status_code == 200:
            data = res.json()
            tracks = data.get("tracks", [])
            logger.info(f"Retrieved {len(tracks)} tracks via device at {device_ip}")
            return tracks
    except Exception as e:
        logger.warning(f"Device proxy track query failed for {device_ip}: {e}")
    return None


def get_available_tracks(discovered_devices=None):
    """
    Get tracks using the best available method:
    1. Direct Google Drive query
    2. Proxy through first online device
    3. Return cached tracks or empty list
    """
    global _cached_tracks

    # Try direct Drive query first
    direct = list_tracks_direct()
    if direct is not None and len(direct) > 0:
        _cached_tracks = direct
        return direct

    # Try proxying via any online discovered device
    if discovered_devices:
        for dev in discovered_devices:
            ip = dev.get("ip")
            port = dev.get("port", 5000)
            if ip:
                tracks = list_tracks_via_device(ip, port)
                if tracks:
                    _cached_tracks = tracks
                    return tracks

    return _cached_tracks
