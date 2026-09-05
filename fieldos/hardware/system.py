from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import socket
import subprocess

from fieldos.hardware.mock import Telemetry


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return None


def _run_text(command: list[str], timeout: float = 1.5) -> str:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return (result.stdout or result.stderr or "").strip()
    except (OSError, subprocess.SubprocessError):
        return ""


@dataclass(slots=True, frozen=True)
class HardwareDetails:
    platform: str
    hostname: str
    interfaces: tuple[str, ...]
    gps: str
    mesh: str
    battery: str
    cpu_temp: str


class SystemTelemetryProvider:
    """Best-effort RVN-01 telemetry with graceful non-Pi fallbacks.

    No optional Python packages are required. On Raspberry Pi OS this reads
    sysfs and common command-line interfaces. Missing hardware is reported as
    NOT PRESENT rather than causing FIELD//OS to fail.
    """

    def read(self) -> Telemetry:
        return Telemetry(
            mesh=self._mesh_status(),
            gps=self._gps_status(),
            network=self._network_status(),
            cpu_temp_c=self._cpu_temp(),
            storage_percent=self._storage_percent(),
            battery_percent=self._battery_percent(),
        )

    def details(self) -> HardwareDetails:
        interfaces = tuple(name for _, name in socket.if_nameindex()) if hasattr(socket, "if_nameindex") else ()
        battery = self._battery_percent()
        temp = self._cpu_temp()
        return HardwareDetails(
            platform=os.uname().machine if hasattr(os, "uname") else os.name,
            hostname=socket.gethostname(),
            interfaces=interfaces,
            gps=self._gps_status(),
            mesh=self._mesh_status(),
            battery="EXTERNAL / UNKNOWN" if battery < 0 else f"{battery}%",
            cpu_temp="UNKNOWN" if temp < 0 else f"{temp:.1f} C",
        )

    def _cpu_temp(self) -> float:
        candidates = [
            Path("/sys/class/thermal/thermal_zone0/temp"),
            Path("/sys/class/hwmon/hwmon0/temp1_input"),
        ]
        for path in candidates:
            value = _read_text(path)
            if not value:
                continue
            try:
                raw = float(value)
                return round(raw / 1000.0 if raw > 200 else raw, 1)
            except ValueError:
                continue
        return -1.0

    def _storage_percent(self) -> int:
        try:
            usage = shutil.disk_usage(Path.home())
            return round((usage.used / usage.total) * 100) if usage.total else 0
        except OSError:
            return 0

    def _battery_percent(self) -> int:
        root = Path("/sys/class/power_supply")
        if not root.exists():
            return -1
        for capacity in sorted(root.glob("BAT*/capacity")):
            value = _read_text(capacity)
            try:
                return int(value) if value is not None else -1
            except ValueError:
                continue
        return -1

    def _network_status(self) -> str:
        sys_net = Path("/sys/class/net")
        if sys_net.exists():
            active: list[str] = []
            for iface in sorted(sys_net.iterdir()):
                if iface.name == "lo":
                    continue
                state = _read_text(iface / "operstate")
                if state == "up":
                    active.append(iface.name)
            if active:
                return ",".join(active[:2]).upper()
        try:
            names = [name for _, name in socket.if_nameindex() if name.lower() not in {"lo", "loopback"}]
            return names[0].upper() if names else "DISCONNECTED"
        except OSError:
            return "DISCONNECTED"

    def _gps_status(self) -> str:
        if shutil.which("gpspipe"):
            output = _run_text(["gpspipe", "-w", "-n", "1"], timeout=2.0)
            if '"class":"TPV"' in output or '"class": "TPV"' in output:
                return "READY"
            if output:
                return "NO FIX"
        if shutil.which("systemctl"):
            if _run_text(["systemctl", "is-active", "gpsd"]) == "active":
                return "GPSD"
        return "NOT PRESENT"

    def _mesh_status(self) -> str:
        if shutil.which("meshtastic"):
            return "CLI READY"
        serial_candidates = list(Path("/dev").glob("ttyACM*")) + list(Path("/dev").glob("ttyUSB*"))
        if serial_candidates:
            return "SERIAL"
        return "NOT PRESENT"


class AutoTelemetryProvider(SystemTelemetryProvider):
    """Production default provider used on both development hosts and RVN-01."""

    pass
