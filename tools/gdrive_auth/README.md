# PlantHead — Google Drive Authorization Tool

This helper tool runs on your laptop/desktop (any computer with a web browser) to generate the OAuth token (`gdrive_token.json`) required by the Raspberry Pi for Google Drive uploads and track downloads.

---

## Quick 3-Step Setup

### Step 1: Download `credentials.json`
1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Select your project and ensure the **Google Drive API** is enabled.
3. Under **OAuth consent screen**, make sure your Google account email is added as a **Test User**.
4. Go to **Credentials** -> **Create Credentials** -> **OAuth client ID**.
5. Application type: **Desktop App** -> Name: `PlantHead` -> Click **Create**.
6. Download the JSON file, rename it to `credentials.json`, and place it in this folder (`tools/gdrive_auth/credentials.json`).

### Step 2: Generate the Token
- **On Windows**: Double-click [`run_auth.bat`](run_auth.bat) (or run `python authorize.py`).
- **On macOS / Linux**: Run `./run_auth.sh` (or `python3 authorize.py`).

A browser window will open automatically:
1. Log in with the Google Account that has access to your PlantHead Google Drive folders.
2. Click **Continue** / **Allow**.
3. Once authorized, the browser will display "The authentication flow has completed."

### Step 3: Where the Token Goes
The script automatically:
1. Generates `gdrive_token.json` in this folder.
2. **Automatically copies** it into [`../../firmware/planthead/secrets/gdrive_token.json`](../../firmware/planthead/secrets/).

> [!TIP]
> Because it is copied into `firmware/planthead/secrets/`, when you transfer `planthead` to your Raspberry Pi, the token is **already in place**!
>
> If your Pi is already running on your network and you just need to copy the token over, double-click [`copy_to_pi.bat`](copy_to_pi.bat).
