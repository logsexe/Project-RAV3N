from __future__ import annotations

import json
import socket
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class GPSSnapshot:
    """One read-only snapshot of the local gpsd state."""

    state: str
    mode: int = 0
    latitude: float | None = None
    longitude: float | None = None
    altitude: float | None = None
    speed: float | None = None
    track: float | None = None
    satellites: int | None = None
    satellites_used: int | None = None
    device: str | None = None
    driver: str | None = None
    subtype: str | None = None

    @property
    def fix_label(self) -> str:
        if self.state != "FIX":
            return self.state
        if self.mode >= 3:
            return "3D FIX"
        return "2D FIX"


def gpsd_snapshot(
    host: str = "127.0.0.1",
    port: int = 2947,
    timeout: float = 0.45,
    sample_window: float = 0.8,
) -> GPSSnapshot:
    """Collect TPV, SKY and DEVICE data from gpsd without blocking the UI.

    gpsd sends each class independently.  A TPV message alone is enough for
    coordinates, while SKY supplies the satellite counts and DEVICE/DEVICES
    supplies receiver identity.  We therefore keep reading briefly instead of
    returning on the first TPV packet.
    """

    mode = 0
    latitude = longitude = altitude = speed = track = None
    satellites = satellites_used = None
    device = driver = subtype = None
    saw_data = False
    buffer = ""

    try:
        with socket.create_connection((host, port), timeout=timeout) as conn:
            conn.settimeout(timeout)
            conn.sendall(b'?WATCH={"enable":true,"json":true};\n')
            deadline = time.monotonic() + sample_window

            while time.monotonic() < deadline:
                try:
                    raw = conn.recv(4096)
                except socket.timeout:
                    continue
                if not raw:
                    break
                buffer += raw.decode(errors="replace")
                lines = buffer.split("\n")
                buffer = lines.pop()

                for line in lines:
                    if not line.strip():
                        continue
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    klass = item.get("class")
                    if klass == "DEVICES":
                        devices = item.get("devices") or []
                        if devices:
                            info = devices[0]
                            device = info.get("path") or device
                            driver = info.get("driver") or driver
                            subtype = info.get("subtype") or subtype
                            saw_data = True
                    elif klass == "DEVICE":
                        device = item.get("path") or device
                        driver = item.get("driver") or driver
                        subtype = item.get("subtype") or subtype
                        saw_data = True
                    elif klass == "TPV":
                        mode = int(item.get("mode", 0) or 0)
                        latitude = item.get("lat", latitude)
                        longitude = item.get("lon", longitude)
                        altitude = item.get("altHAE", item.get("alt", altitude))
                        speed = item.get("speed", speed)
                        track = item.get("track", track)
                        saw_data = True
                    elif klass == "SKY":
                        satellites = item.get("nSat", satellites)
                        satellites_used = item.get("uSat", satellites_used)
                        saw_data = True

                # Once all useful classes have arrived and we have a real fix,
                # no value is added by waiting for the full sample window.
                if mode >= 2 and latitude is not None and longitude is not None and satellites is not None and device:
                    break
    except OSError:
        return GPSSnapshot("GPSD OFFLINE")

    if not saw_data:
        return GPSSnapshot("NO DATA")

    state = "FIX" if mode >= 2 and latitude is not None and longitude is not None else "NO FIX"
    return GPSSnapshot(
        state=state,
        mode=mode,
        latitude=latitude,
        longitude=longitude,
        altitude=altitude,
        speed=speed,
        track=track,
        satellites=satellites,
        satellites_used=satellites_used,
        device=device,
        driver=driver,
        subtype=subtype,
    )
