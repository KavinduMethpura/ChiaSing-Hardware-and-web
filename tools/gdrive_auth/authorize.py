"""
Google Drive OAuth Token Generator for PlantHead.
Run this script on your laptop / desktop (machine with a browser).

It generates `gdrive_token.json` and automatically copies it to
`firmware/planthead/secrets/gdrive_token.json` so your Raspberry Pi can
authenticate with Google Drive headlessly.
"""
import os
import shutil
import sys

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("\n[!] Missing dependencies. Please install required packages:")
    print("    pip install -r requirements.txt\n")
    sys.exit(1)

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.readonly",
]

CREDENTIALS_FILE = "credentials.json"
OUTPUT_TOKEN_FILE = "gdrive_token.json"
FIRMWARE_SECRETS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "firmware", "planthead", "secrets")
)


def main():
    print("=" * 60)
    print(" PlantHead — Google Drive Token Authorization Tool")
    print("=" * 60)

    if not os.path.exists(CREDENTIALS_FILE):
        print(f"\n[ERROR] '{CREDENTIALS_FILE}' not found in {os.path.dirname(os.path.abspath(__file__))}")
        print("\nHow to get 'credentials.json':")
        print("  1. Go to Google Cloud Console (https://console.cloud.google.com/)")
        print("  2. Select/create your project and enable 'Google Drive API'")
        print("  3. Under 'OAuth consent screen', add your Google email as a 'Test User'")
        print("  4. Go to 'Credentials' -> 'Create Credentials' -> 'OAuth client ID'")
        print("  5. Select 'Desktop App', name it 'PlantHead', and click Create")
        print(f"  6. Download the JSON file, rename it to '{CREDENTIALS_FILE}', and place it in this folder.\n")
        sys.exit(1)

    print("\n[1/3] Starting OAuth flow in your default browser...")
    print("Please log in with the Google Account that has access to your PlantHead Drive folders.\n")

    try:
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)

        # 1. Save locally
        with open(OUTPUT_TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
        print(f"[2/3] Successfully saved token to: {os.path.abspath(OUTPUT_TOKEN_FILE)}")

        # 2. Automatically copy to firmware/planthead/secrets/
        if os.path.exists(FIRMWARE_SECRETS_DIR):
            target_path = os.path.join(FIRMWARE_SECRETS_DIR, OUTPUT_TOKEN_FILE)
            shutil.copyfile(OUTPUT_TOKEN_FILE, target_path)
            print(f"[3/3] Automatically copied token to firmware: {target_path}")
        else:
            print(f"[3/3] Note: Firmware directory not found at {FIRMWARE_SECRETS_DIR}")

        print("\n" + "=" * 60)
        print(" Authorization Complete!")
        print(" Now when you copy 'firmware/planthead' to your Raspberry Pi,")
        print(" the token is already in 'secrets/gdrive_token.json'.")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n[ERROR] Authorization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
