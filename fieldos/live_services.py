from __future__ import annotations

import importlib.util
import json
import os
import shutil
import socket
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GPSFix:
    state: str
    latitude: float | None = None
    longitude: float | None = None
    altitude: float | None = None
    speed: float | None = None
    track: float | None = None


@dataclass(frozen=True)
class MeshState:
    state: str
    nodes: int | None = None
    port: str | None = None


@dataclass(frozen=True)
class RadioState:
    state: str
    rtl_sdr: bool = False
    gqrx: bool = False
    sdrpp: bool = False


def _run(args: list[str], timeout: float = 1.5) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None


def system_metrics() -> dict[str, str]:
    if importlib.util.find_spec("psutil") is None:
        return {"PSUTIL": "NOT INSTALLED"}
    import psutil

    vm = psutil.virtual_memory()
    disk = psutil.disk_usage(str(Path.home()))
    result = {
        "CPU": f"{psutil.cpu_percent(interval=None):.0f}%",
        "MEMORY": f"{vm.percent:.0f}%",
        "STORAGE": f"{disk.percent:.0f}%",
        "PSUTIL": "READY",
    }
    try:
        temps = psutil.sensors_temperatures()
        values = [entry.current for entries in temps.values() for entry in entries if entry.current is not None]
        if values:
            result["TEMP"] = f"{max(values):.1f} C"
    except (AttributeError, OSError):
        pass
    return result


def gpsd_fix(host: str = "127.0.0.1", port: int = 2947, timeout: float = 0.45) -> GPSFix:
    try:
        with socket.create_connection((host, port), timeout=timeout) as conn:
            conn.settimeout(timeout)
            conn.sendall(b'?WATCH={"enable":true,"json":true};\n')
            for _ in range(8):
                raw = conn.recv(4096)
                if not raw:
                    break
                for line in raw.decode(errors="replace").splitlines():
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if item.get("class") != "TPV":
                        continue
                    if int(item.get("mode", 0) or 0) < 2:
                        return GPSFix("NO FIX")
                    return GPSFix(
                        "FIX",
                        item.get("lat"), item.get("lon"), item.get("altHAE", item.get("alt")),
                        item.get("speed"), item.get("track"),
                    )
    except OSError:
        return GPSFix("GPSD OFFLINE")
    return GPSFix("NO DATA")


def meshtastic_state() -> MeshState:
    if importlib.util.find_spec("meshtastic") is None:
        return MeshState("NOT INSTALLED")
    candidates: list[str] = []
    if os.name != "nt":
        for pattern in ("/dev/ttyACM*", "/dev/ttyUSB*"):
            candidates.extend(str(path) for path in Path("/dev").glob(Path(pattern).name))
    try:
        from meshtastic.serial_interface import SerialInterface
    except Exception:
        return MeshState("IMPORT ERROR")

    try:
        interface = SerialInterface(devPath=candidates[0] if candidates else None, noProto=False)
        try:
            nodes = getattr(interface, "nodes", {}) or {}
            port_name = getattr(interface, "devPath", None) or (candidates[0] if candidates else None)
            return MeshState("READY", len(nodes), port_name)
        finally:
            interface.close()
    except Exception:
        return MeshState("NO DEVICE")


def radio_state() -> RadioState:
    gqrx = shutil.which("gqrx") is not None
    sdrpp = shutil.which("sdrpp") is not None or shutil.which("SDR++") is not None
    rtl = False
    rtl_test = shutil.which("rtl_test")
    if rtl_test:
        result = _run([rtl_test, "-t"], timeout=1.5)
        if result:
            text = (result.stdout + result.stderr).lower()
            rtl = "found" in text and "device" in text
    state = "READY" if rtl else "NO SDR"
    return RadioState(state, rtl, gqrx, sdrpp)


def zim_files() -> tuple[Path, ...]:
    roots = [
        Path.home() / "Library",
        Path.home() / "library",
        Path.home() / "Kiwix",
        Path.home() / "kiwix",
        Path.home() / "Documents",
        Path.home() / "Project-RAV3N" / "library",
    ]
    found: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        try:
            found.extend(root.rglob("*.zim"))
        except OSError:
            continue
        if len(found) >= 50:
            break
    return tuple(sorted(set(found))[:50])
