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


@dataclass(frozen=True)
class NetworkInterface:
    name: str
    state: str
    address: str | None = None


@dataclass(frozen=True)
class NetworkNeighbour:
    address: str
    device: str
    lladdr: str | None
    state: str


@dataclass(frozen=True)
class MeshNode:
    id: str
    name: str
    last_heard: str | None = None


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


def network_interfaces() -> tuple[NetworkInterface, ...]:
    """List non-loopback interfaces with their best-known address and scope.

    Read-only: this only parses `ip -j address show up`, it never configures
    or probes beyond what the kernel already reports.
    """
    if shutil.which("ip"):
        result = _run(["ip", "-j", "address", "show", "up"])
        if result and result.returncode == 0 and result.stdout.strip():
            try:
                records = json.loads(result.stdout)
            except json.JSONDecodeError:
                records = []
            interfaces: list[NetworkInterface] = []
            for record in records if isinstance(records, list) else []:
                name = str(record.get("ifname", ""))
                if not name or name == "lo":
                    continue
                state, address = "NO ADDRESS", None
                for addr in record.get("addr_info", []) or []:
                    local = str(addr.get("local", ""))
                    scope = str(addr.get("scope", ""))
                    if not local:
                        continue
                    if scope == "global":
                        state, address = "GLOBAL", local
                        break
                    if scope == "link" and state != "GLOBAL":
                        state, address = "LINK LOCAL", local
                interfaces.append(NetworkInterface(name.upper(), state, address))
            return tuple(interfaces)
    try:
        names = [name for _, name in socket.if_nameindex() if name.lower() not in {"lo", "loopback"}]
    except OSError:
        names = []
    return tuple(NetworkInterface(name.upper(), "UNKNOWN") for name in names)


def network_neighbours(limit: int = 25) -> tuple[NetworkNeighbour, ...]:
    """List the local ARP/ND neighbour table. Passive: no probing is sent."""
    if not shutil.which("ip"):
        return ()
    result = _run(["ip", "-j", "neighbour", "show"])
    if not result or result.returncode != 0 or not result.stdout.strip():
        return ()
    try:
        records = json.loads(result.stdout)
    except json.JSONDecodeError:
        return ()
    neighbours: list[NetworkNeighbour] = []
    for record in records if isinstance(records, list) else []:
        dst = str(record.get("dst", ""))
        if not dst:
            continue
        state = record.get("state") or []
        neighbours.append(
            NetworkNeighbour(
                address=dst,
                device=str(record.get("dev", "")),
                lladdr=record.get("lladdr"),
                state=" ".join(state) if state else "UNKNOWN",
            )
        )
        if len(neighbours) >= limit:
            break
    return tuple(neighbours)


def _meshtastic_serial_interface():
    if importlib.util.find_spec("meshtastic") is None:
        return None
    candidates: list[str] = []
    if os.name != "nt":
        for pattern in ("/dev/ttyACM*", "/dev/ttyUSB*"):
            candidates.extend(str(path) for path in Path("/dev").glob(Path(pattern).name))
    try:
        from meshtastic.serial_interface import SerialInterface
    except Exception:
        return None
    try:
        return SerialInterface(devPath=candidates[0] if candidates else None, noProto=False)
    except Exception:
        return None


def meshtastic_nodes() -> tuple[MeshNode, ...]:
    """List known Meshtastic nodes. Read-only: never transmits."""
    interface = _meshtastic_serial_interface()
    if interface is None:
        return ()
    try:
        nodes = getattr(interface, "nodes", {}) or {}
        result: list[MeshNode] = []
        for node_id, info in nodes.items():
            info = info if isinstance(info, dict) else {}
            user = info.get("user", {}) if isinstance(info.get("user"), dict) else {}
            name = user.get("longName") or user.get("shortName") or str(node_id)
            last_heard = info.get("lastHeard")
            result.append(MeshNode(str(node_id), str(name), str(last_heard) if last_heard else None))
        return tuple(result)
    except Exception:
        return ()
    finally:
        try:
            interface.close()
        except Exception:
            pass


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
