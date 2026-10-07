"""
PlantHead Zeroconf Network Discovery Engine.
Listens for mDNS broadcasts of type `_planthead._tcp.local.` and maintains
an in-memory thread-safe registry of all active PlantHead units on the LAN.
"""
import logging
import socket
import threading
import time
import requests
from zeroconf import ServiceBrowser, ServiceListener, Zeroconf

logger = logging.getLogger("planthead.discovery")

SERVICE_TYPE = "_planthead._tcp.local."


class DeviceRegistry:
    def __init__(self):
        self._lock = threading.Lock()
        self._devices = {}  # device_id -> dict
        self._status_cache = {}  # device_id -> status response

    def upsert_device(self, device_id, data):
        with self._lock:
            if device_id in self._devices:
                self._devices[device_id].update(data)
            else:
                self._devices[device_id] = data
            self._devices[device_id]["last_seen"] = time.time()
            logger.info(f"Discovered PlantHead device: {device_id} at {data.get('ip')}:{data.get('port')}")

    def remove_device_by_service_name(self, service_name):
        with self._lock:
            to_delete = None
            for d_id, d in self._devices.items():
                if d.get("service_name") == service_name:
                    to_delete = d_id
                    break
            if to_delete:
                logger.info(f"Device offline/removed: {to_delete}")
                self._devices.pop(to_delete, None)
                self._status_cache.pop(to_delete, None)

    def add_manual_device(self, host, port=5000):
        """Allow manually registering an IP/hostname if multicast is blocked on the router."""
        try:
            url = f"http://{host}:{port}/status"
            res = requests.get(url, timeout=3.0)
            if res.status_code == 200:
                data = res.json()
                device_id = data.get("device_id", f"manual_{host}")
                self.upsert_device(device_id, {
                    "device_id": device_id,
                    "ip": host,
                    "port": port,
                    "manual": True,
                    "service_name": f"{device_id}.manual",
                })
                self.set_status(device_id, data)
                return True, device_id
        except Exception as e:
            logger.error(f"Failed to manually connect to {host}:{port} - {e}")
        return False, None

    def get_devices(self):
        with self._lock:
            # Return copy of devices
            now = time.time()
            res = []
            for d_id, d in self._devices.items():
                item = dict(d)
                item["status_info"] = self._status_cache.get(d_id, {
                    "device_id": d_id,
                    "status": "online",
                    "playback": {"state": "idle", "track": None},
                })
                item["is_active"] = (now - item.get("last_seen", 0)) < 45 or item.get("manual", False)
                res.append(item)
            # Sort alphabetically by device_id (planthead1, planthead2, ...)
            res.sort(key=lambda x: x.get("device_id", ""))
            return res

    def set_status(self, device_id, status_data):
        with self._lock:
            self._status_cache[device_id] = status_data


class PlantHeadListener(ServiceListener):
    def __init__(self, registry: DeviceRegistry):
        self.registry = registry

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        self._resolve(zc, type_, name)

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        self._resolve(zc, type_, name)

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        self.registry.remove_device_by_service_name(name)

    def _resolve(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        if not info:
            return

        ip = None
        if info.addresses:
            try:
                ip = socket.inet_ntoa(info.addresses[0])
            except Exception:
                ip = None

        if not ip:
            return

        port = info.port
        props = {}
        for k, v in info.properties.items():
            k_str = k.decode("utf-8", "ignore") if isinstance(k, bytes) else str(k)
            v_str = v.decode("utf-8", "ignore") if isinstance(v, bytes) else str(v)
            props[k_str] = v_str

        # Device ID from txt-record or fallback to service name
        device_id = props.get("device_id")
        if not device_id:
            # Extract planthead1 from "PlantHead planthead1._planthead._tcp.local."
            clean_name = name.split(".")[0].replace("PlantHead", "").strip()
            device_id = clean_name if clean_name else "planthead"

        self.registry.upsert_device(device_id, {
            "device_id": device_id,
            "service_name": name,
            "ip": ip,
            "port": port,
            "properties": props,
            "manual": False,
        })


class DiscoveryManager:
    def __init__(self):
        self.registry = DeviceRegistry()
        self.zeroconf = None
        self.browser = None
        self._running = False
        self._poller_thread = None

    def start(self):
        if self._running:
            return
        self._running = True
        try:
            self.zeroconf = Zeroconf()
            listener = PlantHeadListener(self.registry)
            self.browser = ServiceBrowser(self.zeroconf, SERVICE_TYPE, listener)
            logger.info(f"Zeroconf discovery started for service {SERVICE_TYPE}")
        except Exception as e:
            logger.error(f"Failed to initialize Zeroconf: {e}")

        # Start background health poller
        self._poller_thread = threading.Thread(target=self._status_poller_loop, daemon=True)
        self._poller_thread.start()

    def _status_poller_loop(self):
        """Poll each discovered device's /status every 4 seconds."""
        while self._running:
            devices = self.registry.get_devices()
            for dev in devices:
                ip = dev.get("ip")
                port = dev.get("port", 5000)
                device_id = dev.get("device_id")
                if not ip or not device_id:
                    continue
                try:
                    url = f"http://{ip}:{port}/status"
                    res = requests.get(url, timeout=2.5)
                    if res.status_code == 200:
                        status_data = res.json()
                        self.registry.set_status(device_id, status_data)
                        self.registry.upsert_device(device_id, {"last_seen": time.time()})
                except Exception:
                    # Device might be momentarily offline or slow
                    pass
            time.sleep(3.0)

    def stop(self):
        self._running = False
        if self.browser:
            self.browser.cancel()
        if self.zeroconf:
            self.zeroconf.close()
        logger.info("Zeroconf discovery stopped")
