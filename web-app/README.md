# PlantHead — Multi-Device Controller Web App (Phase 3)

The local web application automatically discovers all active Raspberry Pi PlantHead units (`planthead1` through `planthead5`) on your current Wi-Fi network, lists available audio tracks from the shared Google Drive music library, and allows you or a collaborator to dispatch playback commands with zero network configuration.

---

## Features

- **Zeroconf Auto-Discovery**: Listens for `_planthead._tcp` mDNS broadcasts; automatically lists every reachable Pi unit on the network without typing IP addresses.
- **Shared Music Library**: Reads available audio files directly from Google Drive (or proxies through discovered Pis).
- **Independent & Synchronized Control**:
  - Pick a target device, choose a track, and send playback commands with one click.
  - Live status indicator with dynamic audio visualizer equalizer for active playback.
  - "Stop All" emergency stop to halt audio playback across all units simultaneously.
- **Manual IP Fallback**: If a restrictive venue or router blocks mDNS multicast, easily connect by typing the device's IP.
- **Zero Config for Collaborators**: Runs locally on any laptop (Windows, Mac, Linux) with Python installed.

---

## Quick Start

### On Windows
Double-click:
```bat
start_web_app.bat
```
*(This creates a virtual environment, installs dependencies, opens your browser to `http://localhost:8080`, and starts the controller).*

### On macOS / Linux
Run:
```bash
chmod +x start.sh
./start.sh
```

---

## Architecture Flow

```
[ Laptop Web App ]  (running at http://localhost:8080)
       │
       ├── Zeroconf Browser ──► Discovers all `_planthead._tcp` services on LAN
       │
       ├── GET /tracks       ──► Reads shared music tracks from Google Drive
       │
       └── POST /play        ──► Dispatches playback directly to target Pi:
                                  http://<pi_ip>:5000/play
                                    └── Pi downloads from Drive (or local cache)
                                    └── Pi plays through MAX98357A speaker amp
```
