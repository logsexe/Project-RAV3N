from __future__ import annotations

import importlib.util
import platform
import shutil
import socket
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from .live_services import gpsd_fix, meshtastic_state, radio_state, system_metrics, zim_files


@dataclass(frozen=True)
class HealthSnapshot:
    sections: dict[str, list[tuple[str, str]]]


def _run(args: list[str], timeout: float = 1.2) -> tuple[int, str]:
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
        return result.returncode, (result.stdout + result.stderr).strip()
    except (OSError, subprocess.TimeoutExpired):
        return 127, ""


def _primary_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("192.0.2.1", 9))
        return sock.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "--"
    finally:
        sock.close()


def _service_state(name: str) -> str:
    if shutil.which("systemctl") is None:
        return "--"
    code, text = _run(["systemctl", "is-active", name], timeout=0.8)
    return "READY" if code == 0 and text.strip() == "active" else "OFFLINE"


def _uptime() -> str:
    try:
        seconds = int(float(Path("/proc/uptime").read_text().split()[0]))
    except (OSError, ValueError, IndexError):
        return "--"
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    return f"{days}d {hours:02d}:{minutes:02d}" if days else f"{hours:02d}:{minutes:02d}"


def _memory_detail() -> str:
    if importlib.util.find_spec("psutil") is None:
        return "--"
    import psutil
    vm = psutil.virtual_memory()
    return f"{vm.used / 1024**3:.1f}/{vm.total / 1024**3:.1f} GiB"


def _storage_detail() -> str:
    try:
        usage = shutil.disk_usage(Path.home())
        return f"{usage.used / 1024**3:.1f}/{usage.total / 1024**3:.1f} GiB"
    except OSError:
        return "--"


def _power_state() -> tuple[str, str]:
    if shutil.which("vcgencmd") is None:
        return "--", "--"
    _, throttled = _run(["vcgencmd", "get_throttled"])
    _, voltage = _run(["vcgencmd", "measure_volts", "core"])
    throttle_value = throttled.partition("=")[2].strip() if "=" in throttled else throttled
    throttle = "OK" if throttle_value in {"0x0", "0"} else (throttle_value or "--")
    voltage_value = voltage.partition("=")[2].strip() if "=" in voltage else (voltage or "--")
    return throttle, voltage_value


def _usb_summary() -> tuple[str, str]:
    if shutil.which("lsusb") is None:
        return "--", "--"
    code, text = _run(["lsusb"], timeout=1.0)
    if code != 0:
        return "ERROR", "--"
    lines = [line for line in text.splitlines() if line.strip()]
    hub = "READY" if any("hub" in line.lower() for line in lines) else "DETECTED" if lines else "NONE"
    return hub, str(len(lines))


def collect_health_snapshot() -> HealthSnapshot:
    metrics = system_metrics()
    gps = gpsd_fix()
    mesh = meshtastic_state()
    radio = radio_state()
    throttle, core_voltage = _power_state()
    usb_hub, usb_devices = _usb_summary()

    bluetooth = _service_state("bluetooth.service")
    ssh = _service_state("ssh.service")
    mdns = _service_state("avahi-daemon.service")
    gpsd = "READY" if gps.state in {"FIX", "NO FIX", "NO DATA"} else "OFFLINE"
    mesh_ready = "READY" if mesh.state == "READY" else mesh.state
    sdr_ready = "READY" if radio.rtl_sdr else "NOT DETECTED"
    kiwix = "READY" if shutil.which("kiwix-serve") or zim_files() else "NOT INSTALLED"

    audio = "--"
    if shutil.which("aplay"):
        code, text = _run(["aplay", "-l"], timeout=1.0)
        if code == 0:
            audio = "READY" if "card" in text.lower() else "NO DEVICE"

    sections = {
        "SYSTEM": [
            ("HOST", socket.gethostname()),
            ("OS", f"{platform.system()} {platform.release()}"),
            ("ARCH", platform.machine()),
            ("UPTIME", _uptime()),
            ("CPU", metrics.get("CPU", "--")),
            ("TEMP", metrics.get("TEMP", "--")),
            ("MEMORY", _memory_detail()),
            ("STORAGE", _storage_detail()),
        ],
        "POWER": [
            ("THROTTLE", throttle),
            ("CORE V", core_voltage),
        ],
        "HARDWARE": [
            ("GPS", gps.state),
            ("SDR", sdr_ready),
            ("MESH", mesh_ready),
            ("AUDIO", audio),
            ("BLUETOOTH", bluetooth),
        ],
        "USB": [
            ("HUB", usb_hub),
            ("DEVICES", usb_devices),
        ],
        "NETWORK": [
            ("PRIMARY IP", _primary_ip()),
            ("SSH", ssh),
            ("MDNS", mdns),
        ],
        "SERVICES": [
            ("FIELD//OS", "READY"),
            ("GPSD", gpsd),
            ("MESHTASTIC", mesh_ready),
            ("KIWIX", kiwix),
        ],
    }
    return HealthSnapshot(sections)
