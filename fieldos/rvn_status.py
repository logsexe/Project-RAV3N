from __future__ import annotations

from dataclasses import dataclass
import importlib.util
import platform
from pathlib import Path
import shutil
import socket
import subprocess
import time

from .live_services import gpsd_fix, meshtastic_state, radio_state, system_metrics


@dataclass(frozen=True)
class RVNStatus:
    system: tuple[tuple[str, str], ...]
    power: tuple[tuple[str, str], ...]
    hardware: tuple[tuple[str, str], ...]
    usb: tuple[tuple[str, str], ...]
    network: tuple[tuple[str, str], ...]
    services: tuple[tuple[str, str], ...]


def _run(args: list[str], timeout: float = 1.0) -> str:
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return (result.stdout or result.stderr or "").strip()


def _service(name: str) -> str:
    if shutil.which("systemctl") is None:
        return "UNKNOWN"
    text = _run(["systemctl", "is-active", name], timeout=0.8)
    return "READY" if text == "active" else (text.upper() if text else "NOT FOUND")


def _primary_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("192.0.2.1", 9))
        return sock.getsockname()[0]
    except OSError:
        return "--"
    finally:
        sock.close()


def _uptime() -> str:
    try:
        seconds = int(float(Path("/proc/uptime").read_text().split()[0]))
    except (OSError, ValueError, IndexError):
        return "--"
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, _ = divmod(seconds, 60)
    return f"{days}d {hours:02d}:{minutes:02d}" if days else f"{hours:02d}:{minutes:02d}"


def _throttle() -> str:
    vcgencmd = shutil.which("vcgencmd")
    if not vcgencmd:
        return "UNKNOWN"
    text = _run([vcgencmd, "get_throttled"], timeout=0.8).lower()
    if "0x0" in text:
        return "NO"
    return text.replace("throttled=", "").upper() or "UNKNOWN"


def _usb_count() -> int:
    lsusb = shutil.which("lsusb")
    if lsusb:
        text = _run([lsusb], timeout=1.0)
        if text:
            return len([line for line in text.splitlines() if line.strip()])
    root = Path("/sys/bus/usb/devices")
    if not root.exists():
        return 0
    return sum(1 for item in root.iterdir() if item.name[:1].isdigit() and ":" not in item.name)


def _audio_state() -> str:
    cards = Path("/proc/asound/cards")
    try:
        text = cards.read_text(errors="replace")
    except OSError:
        text = ""
    return "READY" if text.strip() and "no soundcards" not in text.lower() else "NOT DETECTED"


def _interface_state(name: str) -> str:
    path = Path("/sys/class/net") / name / "operstate"
    try:
        return path.read_text().strip().upper()
    except OSError:
        return "NOT PRESENT"


def collect_rvn_status() -> RVNStatus:
    metrics = system_metrics()
    gps = gpsd_fix(timeout=0.25)
    radio = radio_state()

    # Meshtastic probing can be more expensive than the other checks. It remains
    # explicit and failure-tolerant, and this whole snapshot runs off the UI thread.
    try:
        mesh = meshtastic_state()
        mesh_state = mesh.state
    except Exception:
        mesh_state = "ERROR"

    host = socket.gethostname()
    py = platform.python_version()

    system = (
        ("HOST", host),
        ("OS", f"{platform.system()} {platform.release()}"),
        ("ARCH", platform.machine()),
        ("PYTHON", py),
        ("CPU", metrics.get("CPU", "--")),
        ("TEMP", metrics.get("TEMP", "--")),
        ("MEMORY", metrics.get("MEMORY", "--")),
        ("STORAGE", metrics.get("STORAGE", "--")),
        ("UPTIME", _uptime()),
    )

    power = (
        ("SOURCE", "USB-C / EXTERNAL"),
        ("VOLTAGE", "--"),
        ("CURRENT", "--"),
        ("THROTTLED", _throttle()),
    )

    hardware = (
        ("GPS", gps.state),
        ("SDR", "READY" if radio.rtl_sdr else "NOT DETECTED"),
        ("MESH", mesh_state),
        ("AUDIO", _audio_state()),
        ("BLUETOOTH", _service("bluetooth.service")),
    )

    usb = (
        ("DEVICES", str(_usb_count())),
        ("HUB", "CHECKED" if _usb_count() >= 2 else "--"),
    )

    network = (
        ("PRIMARY IP", _primary_ip()),
        ("WLAN0", _interface_state("wlan0")),
        ("ETH0", _interface_state("eth0")),
        ("SSH", _service("ssh.service")),
        ("MDNS", _service("avahi-daemon.service")),
    )

    services = (
        ("FIELD//OS", _service("fieldos-appliance.service")),
        ("GPSD", _service("gpsd.service")),
        ("MESHTASTIC", "READY" if importlib.util.find_spec("meshtastic") else "NOT INSTALLED"),
        ("KIWIX", "READY" if shutil.which("kiwix-serve") else "NOT INSTALLED"),
    )

    return RVNStatus(system, power, hardware, usb, network, services)
