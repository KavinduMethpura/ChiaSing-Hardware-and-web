/**
 * PlantHead Web App — Controller Script
 * Real-time Zeroconf device polling, track browsing, and playback dispatch.
 */

// Global State
let discoveredDevices = [];
let availableTracks = [];
let isPollingActive = true;

// DOM Elements
const devicesContainer = document.getElementById('devices-container');
const tracksContainer = document.getElementById('tracks-container');
const activeDeviceCount = document.getElementById('active-device-count');
const trackCountBadge = document.getElementById('track-count-badge');
const trackSearchInput = document.getElementById('track-search-input');
const btnRefresh = document.getElementById('btn-refresh');
const btnStopAll = document.getElementById('btn-stop-all');
const btnManualIp = document.getElementById('btn-manual-ip');

// Modal Elements
const manualModal = document.getElementById('manual-modal');
const modalCloseBtn = document.getElementById('modal-close-btn');
const modalCancelBtn = document.getElementById('modal-cancel-btn');
const manualForm = document.getElementById('manual-form');
const manualHostInput = document.getElementById('manual-host-input');
const manualPortInput = document.getElementById('manual-port-input');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  setupEventListeners();
  loadData();
  startPolling();
});

function setupEventListeners() {
  btnRefresh.addEventListener('click', () => {
    btnRefresh.classList.add('loading');
    loadData().finally(() => {
      btnRefresh.classList.remove('loading');
      showToast('Network scan refreshed');
    });
  });

  btnStopAll.addEventListener('click', stopAllPlayback);

  trackSearchInput.addEventListener('input', () => {
    renderTracks();
  });

  // Modal handlers
  btnManualIp.addEventListener('click', () => {
    manualModal.classList.add('open');
    manualHostInput.focus();
  });

  const closeModal = () => manualModal.classList.remove('open');
  modalCloseBtn.addEventListener('click', closeModal);
  modalCancelBtn.addEventListener('click', closeModal);

  manualModal.addEventListener('click', (e) => {
    if (e.target === manualModal) closeModal();
  });

  manualForm.addEventListener('submit', (e) => {
    e.preventDefault();
    handleManualConnect();
  });
}

function startPolling() {
  setInterval(() => {
    if (isPollingActive) {
      pollDevices();
    }
  }, 2500);
}

async function loadData() {
  await Promise.all([pollDevices(), loadTracks()]);
}

// --------------------------------------------------------------------------
// Devices API & Rendering
// --------------------------------------------------------------------------

async function pollDevices() {
  try {
    const res = await fetch('/api/devices');
    const data = await res.json();
    discoveredDevices = data.devices || [];
    renderDevices();
    updateHeaderBadge();
  } catch (err) {
    console.error('Error polling devices:', err);
  }
}

function updateHeaderBadge() {
  const count = discoveredDevices.length;
  activeDeviceCount.textContent = `${count} ${count === 1 ? 'Unit' : 'Units'} Online`;
}

function renderDevices() {
  if (discoveredDevices.length === 0) {
    devicesContainer.innerHTML = `
      <div class="empty-state">
        <div class="radar-scan">
          <div class="radar-circle circle-1"></div>
          <div class="radar-circle circle-2"></div>
          <div class="radar-beam"></div>
        </div>
        <h3>Listening for PlantHead units...</h3>
        <p>Ensure your Raspberry Pis are powered on and connected to the same Wi-Fi.<br>
           You can also use <strong>+ Add by IP</strong> to connect directly.</p>
      </div>
    `;
    return;
  }

  devicesContainer.innerHTML = '';

  discoveredDevices.forEach((dev) => {
    const statusInfo = dev.status_info || {};
    const playback = statusInfo.playback || { state: 'idle' };
    const isPlaying = playback.state === 'playing';
    const currentTrack = playback.track;
    const elapsed = playback.elapsed_sec ? `${playback.elapsed_sec}s` : '';

    const card = document.createElement('div');
    card.className = `device-card ${isPlaying ? 'playing' : ''}`;
    card.id = `card-${dev.device_id}`;

    card.innerHTML = `
      <div class="device-top-row">
        <div class="device-id-badge">
          <span class="status-indicator"></span>
          <h3>${dev.device_id}</h3>
          <span class="ip-tag">${dev.ip}:${dev.port}</span>
        </div>
        <div class="device-status-pill">
          ${isPlaying ? `
            <div class="equalizer">
              <span class="eq-bar"></span>
              <span class="eq-bar"></span>
              <span class="eq-bar"></span>
              <span class="eq-bar"></span>
            </div>
            <span>Playing</span>
          ` : `
            <span class="status-indicator" style="background: #64748b; box-shadow: none;"></span>
            <span>Idle</span>
          `}
        </div>
      </div>

      ${isPlaying && currentTrack ? `
        <div class="now-playing-box">
          <div class="track-info">
            <svg class="track-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
              <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path>
            </svg>
            <span class="track-title">${currentTrack.name || currentTrack.id}</span>
          </div>
          <span class="elapsed-time">${elapsed}</span>
        </div>
      ` : ''}

      <div class="device-footer">
        <div class="device-feeds-info">
          Feed: ${statusInfo.feeds?.soil_moisture || dev.device_id}
        </div>
        <div class="device-actions">
          ${isPlaying ? `
            <button class="btn btn-danger btn-sm" onclick="stopPlayback('${dev.device_id}')">
              Stop
            </button>
          ` : `
            <button class="btn btn-secondary btn-sm" onclick="promptPlayOnDevice('${dev.device_id}')">
              Select Track
            </button>
          `}
        </div>
      </div>
    `;

    devicesContainer.appendChild(card);
  });
}

// --------------------------------------------------------------------------
// Tracks API & Rendering
// --------------------------------------------------------------------------

async function loadTracks() {
  try {
    const res = await fetch('/api/tracks');
    const data = await res.json();
    availableTracks = data.tracks || [];
    trackCountBadge.textContent = `${availableTracks.length} Tracks`;
    renderTracks();
  } catch (err) {
    console.error('Error loading tracks:', err);
    tracksContainer.innerHTML = `
      <div class="empty-state">
        <p>No tracks found or Drive credentials not configured yet.<br>
           Add MP3/WAV tracks to your shared Drive music folder.</p>
      </div>
    `;
  }
}

function renderTracks() {
  const searchTerm = trackSearchInput.value.toLowerCase().trim();
  const filtered = availableTracks.filter((t) =>
    (t.name || '').toLowerCase().includes(searchTerm)
  );

  if (filtered.length === 0) {
    tracksContainer.innerHTML = `
      <div class="empty-state">
        <p>No tracks matching "<strong>${searchTerm}</strong>"</p>
      </div>
    `;
    return;
  }

  tracksContainer.innerHTML = '';

  filtered.forEach((track) => {
    const item = document.createElement('div');
    item.className = 'track-item';
    item.id = `track-${track.id}`;

    const sizeMb = track.size ? `${(track.size / (1024 * 1024)).toFixed(1)} MB` : '';
    const ext = track.name.split('.').pop().toUpperCase();

    // Generate device selector options
    let deviceOptions = '';
    if (discoveredDevices.length > 0) {
      deviceOptions = discoveredDevices
        .map((d) => `<option value="${d.device_id}">${d.device_id}</option>`)
        .join('');
    } else {
      deviceOptions = '<option value="">No devices online</option>';
    }

    item.innerHTML = `
      <div class="track-meta">
        <span class="track-name" title="${track.name}">${track.name}</span>
        <div class="track-tags">
          <span>${ext}</span>
          ${sizeMb ? `<span>&bull; ${sizeMb}</span>` : ''}
        </div>
      </div>

      <div class="track-actions">
        <select class="select-target-device" id="select-device-${track.id}">
          ${deviceOptions}
        </select>
        <button class="btn btn-primary" onclick="playTrack('${track.id}', '${escapeQuotes(track.name)}')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
            <polygon points="5 3 19 12 5 21 5 3"></polygon>
          </svg>
          Play
        </button>
      </div>
    `;

    tracksContainer.appendChild(item);
  });
}

function escapeQuotes(str) {
  return (str || '').replace(/'/g, "\\'").replace(/"/g, '&quot;');
}

// --------------------------------------------------------------------------
// Playback Control Handlers
// --------------------------------------------------------------------------

async function playTrack(fileId, fileName) {
  const selectElem = document.getElementById(`select-device-${fileId}`);
  const targetDeviceId = selectElem ? selectElem.value : null;

  if (!targetDeviceId) {
    showToast('Please select an online PlantHead unit first', 'error');
    return;
  }

  showToast(`Downloading & playing "${fileName}" on ${targetDeviceId}...`);

  try {
    const res = await fetch('/api/play', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        device_id: targetDeviceId,
        file_id: fileId,
        file_name: fileName,
      }),
    });

    const data = await res.json();
    if (res.ok && data.success) {
      showToast(`Playing on ${targetDeviceId}!`);
      pollDevices();
    } else {
      showToast(data.error || 'Failed to start playback', 'error');
    }
  } catch (err) {
    showToast(`Network error: ${err.message}`, 'error');
  }
}

async function stopPlayback(deviceId) {
  try {
    const res = await fetch('/api/stop', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ device_id: deviceId }),
    });
    const data = await res.json();
    if (res.ok) {
      showToast(`Playback stopped on ${deviceId}`);
      pollDevices();
    } else {
      showToast(data.error || 'Failed to stop playback', 'error');
    }
  } catch (err) {
    showToast(`Error: ${err.message}`, 'error');
  }
}

async function stopAllPlayback() {
  if (discoveredDevices.length === 0) return;

  try {
    await fetch('/api/stop-all', { method: 'POST' });
    showToast('Stop command sent to all units');
    pollDevices();
  } catch (err) {
    showToast('Failed to stop all units', 'error');
  }
}

function promptPlayOnDevice(deviceId) {
  // Highlight track list
  trackSearchInput.focus();
  showToast(`Select a track above to play on ${deviceId}`);
}

// --------------------------------------------------------------------------
// Manual Connection Handler
// --------------------------------------------------------------------------

async function handleManualConnect() {
  const host = manualHostInput.value.trim();
  const port = parseInt(manualPortInput.value.trim(), 10) || 5000;

  if (!host) return;

  showToast(`Connecting to http://${host}:${port}...`);

  try {
    const res = await fetch('/api/devices/manual', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ host, port }),
    });

    const data = await res.json();
    if (res.ok && data.success) {
      showToast(`Connected to ${data.device_id}!`);
      manualModal.classList.remove('open');
      manualHostInput.value = '';
      pollDevices();
    } else {
      showToast(data.error || 'Could not connect to device', 'error');
    }
  } catch (err) {
    showToast(`Connection failed: ${err.message}`, 'error');
  }
}

// --------------------------------------------------------------------------
// Toast Notifications
// --------------------------------------------------------------------------

function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type === 'error' ? 'error' : ''}`;
  toast.textContent = message;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}
