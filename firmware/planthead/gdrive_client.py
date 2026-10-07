"""
Google Drive Client for PlantHead.
Handles:
  1. Uploading captured images and recorded audio segments to Google Drive.
  2. Listing music tracks from a shared Google Drive folder for web playback.
  3. Downloading selected music tracks to local cache for playback via speaker.

Uses OAuth user credentials (token generated once on a browser machine and stored in secrets/gdrive_token.json).
"""
import io
import logging
import mimetypes
import os
import re

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

import config

logger = logging.getLogger("planthead.gdrive_client")

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.readonly",
]
TOKEN_PATH = "secrets/gdrive_token.json"

_service = None


def get_service():
    """Lazily create and reuse a single Drive API client instance."""
    global _service
    if _service is not None:
        return _service

    if not os.path.exists(TOKEN_PATH):
        raise RuntimeError(
            f"No token found at {TOKEN_PATH}. Generate one on a machine "
            f"with a browser and copy it to {TOKEN_PATH} — the Pi "
            f"cannot run an interactive login."
        )

    creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(TOKEN_PATH, "w") as f:
                f.write(creds.to_json())
            logger.info("Refreshed Google Drive OAuth token")
        else:
            raise RuntimeError(
                f"Token at {TOKEN_PATH} is invalid and cannot be refreshed. "
                f"Please regenerate it on your computer and copy it back."
            )

    _service = build("drive", "v3", credentials=creds)
    return _service


def upload_file(filepath, folder_id=None):
    """
    Upload a local file (image or audio) to the specified Drive folder.
    Returns the uploaded file's Drive ID on success, or None on failure.
    Never raises — allows background loops to continue uninterrupted.
    """
    target_folder = folder_id or config.GDRIVE_IMAGES_FOLDER_ID
    if not target_folder:
        logger.warning(f"No Google Drive folder ID specified for upload of {filepath}")
        return None

    try:
        service = get_service()
        filename = os.path.basename(filepath)

        mime, _ = mimetypes.guess_type(filepath)
        mime = mime or "application/octet-stream"

        file_metadata = {"name": filename, "parents": [target_folder]}
        media = MediaFileUpload(filepath, mimetype=mime, resumable=True)

        uploaded = service.files().create(
            body=file_metadata, media_body=media, fields="id"
        ).execute()

        file_id = uploaded.get("id")
        logger.info(f"Uploaded {filename} to Google Drive folder {target_folder} (id: {file_id})")
        return file_id

    except Exception as e:
        logger.error(f"Google Drive upload failed for {filepath}: {e}")
        return None


def list_music_tracks(folder_id=None):
    """
    Lists audio files in the shared Google Drive music folder.
    Returns a list of dicts: [{'id': ..., 'name': ..., 'size': ..., 'mimeType': ...}]
    """
    target_folder = folder_id or config.GDRIVE_MUSIC_FOLDER_ID
    if not target_folder:
        logger.warning("GDRIVE_MUSIC_FOLDER_ID is not configured in config.py / .env")
        return []

    try:
        service = get_service()
        query = f"'{target_folder}' in parents and trashed = false"
        results = service.files().list(
            q=query,
            pageSize=100,
            fields="files(id, name, mimeType, size)",
            orderBy="name",
        ).execute()

        files = results.get("files", [])
        logger.info(f"Retrieved {len(files)} tracks from Google Drive music folder")
        return files
    except Exception as e:
        logger.error(f"Failed to list music tracks from Google Drive: {e}")
        return []


def download_file(file_id, dest_path=None):
    """
    Download a file from Google Drive by its file ID.
    Caches downloaded files locally in config.MUSIC_SAVE_DIR.
    Returns the absolute or relative local path on success, None on error.
    """
    os.makedirs(config.MUSIC_SAVE_DIR, exist_ok=True)

    try:
        service = get_service()

        # Retrieve file metadata to determine original filename
        meta = service.files().get(fileId=file_id, fields="id, name").execute()
        original_name = meta.get("name", f"track_{file_id}")
        safe_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', original_name)

        if not dest_path:
            dest_path = os.path.join(config.MUSIC_SAVE_DIR, f"{file_id}_{safe_name}")

        # Check local cache
        if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
            logger.info(f"Track {original_name} already in local cache: {dest_path}")
            return dest_path

        logger.info(f"Downloading {original_name} (id: {file_id}) from Google Drive...")
        request = service.files().get_media(fileId=file_id)
        
        with io.FileIO(dest_path, "wb") as fh:
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    logger.debug(f"Download {int(status.progress() * 100)}%")

        logger.info(f"Finished downloading {original_name} to {dest_path}")
        return dest_path

    except Exception as e:
        logger.error(f"Failed to download file {file_id} from Google Drive: {e}")
        if dest_path and os.path.exists(dest_path):
            try:
                os.remove(dest_path)
            except OSError:
                pass
        return None
