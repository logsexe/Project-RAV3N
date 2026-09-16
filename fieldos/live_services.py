from __future__ import annotations

import importlib.util
import json
import os
import shutil
import socket
import subprocess
import sys
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


# rtnetlink address scope values (include/uapi/linux/rtnetlink.h). These are
# a stable kernel ABI, so we compare against the raw integers pyroute2 hands
# back rather than reaching into a pyroute2 constant table for the names
# `ip -j` prints ("global"/"link").
_RT_SCOPE_UNIVERSE = 0
_RT_SCOPE_LINK = 253

# Neighbour-cache state bits (include/uapi/linux/neighbour.h, the NUD_*
# flags). Also a stable kernel ABI - decoded locally for the same reason as
# the scope values above, and named to match what `ip -j neighbour show`
# already puts in its "state" list (e.g. ["REACHABLE"]).
_NUD_STATE_BITS: tuple[tuple[int, str], ...] = (
    (0x01, "INCOMPLETE"),
    (0x02, "REACHABLE"),
    (0x04, "STALE"),
    (0x08, "DELAY"),
    (0x10, "PROBE"),
    (0x20, "FAILED"),
    (0x40, "NOARP"),
    (0x80, "PERMANENT"),
)


def _describe_neighbour_state(bitmask: int) -> str:
    names = [name for bit, name in _NUD_STATE_BITS if bitmask & bit]
    return " ".join(names) if names else "UNKNOWN"


def _pyroute2_usable() -> bool:
    return sys.platform == "linux" and importlib.util.find_spec("pyroute2") is not None


def _pyroute2_interfaces() -> tuple[NetworkInterface, ...] | None:
    """Enumerate up, non-loopback interfaces straight over netlink.

    Same classification rules as the `ip -j` path below (GLOBAL beats LINK
    LOCAL beats NO ADDRESS). Returns None - never an empty tuple - when
    pyroute2 is missing or anything about the call fails, so the caller can
    fall through to the next path instead of reporting "no interfaces" when
    the real answer is "couldn't ask".
    """
    if not _pyroute2_usable():
        return None
    try:
        from pyroute2 import IPRoute

        with IPRoute() as ipr:
            links = ipr.get_links()
            addrs = ipr.get_addr()

        addrs_by_index: dict[int, list] = {}
        for addr in addrs:
            index = addr.get("index")
            if index is None:
                continue
            addrs_by_index.setdefault(index, []).append(addr)

        interfaces: list[NetworkInterface] = []
        for link in links:
            if not (link.get("flags", 0) & 0x1):  # IFF_UP
                continue
            name = str(link.get_attr("IFLA_IFNAME") or "")
            if not name or name.lower() in {"lo", "loopback"}:
                continue
            state, address = "NO ADDRESS", None
            for addr in addrs_by_index.get(link.get("index"), []):
                local = addr.get_attr("IFA_LOCAL") or addr.get_attr("IFA_ADDRESS")
                if not local:
                    continue
                scope = addr.get("scope")
                if scope == _RT_SCOPE_UNIVERSE:
                    state, address = "GLOBAL", str(local)
                    break
                if scope == _RT_SCOPE_LINK and state != "GLOBAL":
                    state, address = "LINK LOCAL", str(local)
            interfaces.append(NetworkInterface(name.upper(), state, address))
        return tuple(interfaces)
    except Exception:
        return None


def network_interfaces() -> tuple[NetworkInterface, ...]:
    """List non-loopback interfaces with their best-known address and scope.

    Tries pyroute2 first (native netlink, Linux-only): no subprocess, and no
    dependency on a particular `ip` build actually shipping `-j` JSON support
    (some minimal/embedded iproute2 builds don't). Falls back to parsing
    `ip -j address show up`, and finally to bare interface names via
    `socket.if_nameindex()` if neither works. Read-only in every path: this
    only ever reads what the kernel already reports, never configures or
    probes anything.
    """
    pyroute2_result = _pyroute2_interfaces()
    if pyroute2_result is not None:
        return pyroute2_result
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


def _pyroute2_neighbours(limit: int) -> tuple[NetworkNeighbour, ...] | None:
    """Read the ARP/ND table straight over netlink. Passive: no probing is sent.

    Returns None - never an empty tuple - when pyroute2 is missing or the
    call fails, so the caller falls through instead of reporting "no
    neighbours" when the real answer is "couldn't ask".
    """
    if not _pyroute2_usable():
        return None
    try:
        from pyroute2 import IPRoute

        with IPRoute() as ipr:
            records = ipr.get_neighbours()
            links = ipr.get_links()

        names_by_index = {link.get("index"): str(link.get_attr("IFLA_IFNAME") or "") for link in links}

        neighbours: list[NetworkNeighbour] = []
        for record in records:
            dst = record.get_attr("NDA_DST") or ""
            if not dst:
                continue
            neighbours.append(
                NetworkNeighbour(
                    address=str(dst),
                    device=names_by_index.get(record.get("ifindex"), ""),
                    lladdr=record.get_attr("NDA_LLADDR"),
                    state=_describe_neighbour_state(record.get("state", 0) or 0),
                )
            )
            if len(neighbours) >= limit:
                break
        return tuple(neighbours)
    except Exception:
        return None


def network_neighbours(limit: int = 25) -> tuple[NetworkNeighbour, ...]:
    """List the local ARP/ND neighbour table. Passive: no probing is sent.

    Tries pyroute2 first (native netlink, Linux-only), falling back to
    parsing `ip -j neighbour show`. See network_interfaces() for why.
    """
    pyroute2_result = _pyroute2_neighbours(limit)
    if pyroute2_result is not None:
        return pyroute2_result
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


def open_meshtastic_interface():
    """Open a Meshtastic serial connection, or None if unavailable.

    Used both for a single probe (meshtastic_nodes(), which closes it
    straight away) and to hand back a persistent connection a caller keeps
    open across a session (see qt_field_app.py's MESH CONNECT action).
    """
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
    interface = open_meshtastic_interface()
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
