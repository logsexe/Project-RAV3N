from __future__ import annotations

from dataclasses import dataclass
import json
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

    Mesh detection is intentionally conservative. Generic USB/ACM serial ports
    are not treated as Meshtastic hardware because RVN-01 may also expose GPS,
    debug adapters, microcontrollers, or other serial peripherals. An operator
    can explicitly bind a mesh device with FIELDOS_MESH_DEVICE.
    """

    MESH_DEVICE_ENV = "FIELDOS_MESH_DEVICE"

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
        """Report an interface as ready only when it has a usable IP address.

        FIELD//OS deliberately avoids an external connectivity probe so an
        isolated field LAN can still be considered usable. A physical link with
        no address is reported separately and remains degraded in the UI.
        """
        if shutil.which("ip"):
            output = _run_text(["ip", "-j", "address", "show", "up"])
            if output:
                try:
                    records = json.loads(output)
                except (json.JSONDecodeError, TypeError):
                    records = []
                link_only = False
                link_local = False
                for record in records if isinstance(records, list) else []:
                    name = str(record.get("ifname", ""))
                    if not name or name == "lo":
                        continue
                    link_only = True
                    for addr in record.get("addr_info", []) or []:
                        local = str(addr.get("local", ""))
                        scope = str(addr.get("scope", ""))
                        if not local:
                            continue
                        if scope == "global":
                            return name.upper()
                        if scope == "link":
                            link_local = True
                if link_local:
                    return "LINK LOCAL"
                if link_only:
                    return "NO ADDRESS"

        sys_net = Path("/sys/class/net")
        if sys_net.exists():
            for iface in sorted(sys_net.iterdir()):
                if iface.name == "lo":
                    continue
                if _read_text(iface / "operstate") == "up":
                    return "LINK UP"
            return "DISCONNECTED"

        try:
            names = [name for _, name in socket.if_nameindex() if name.lower() not in {"lo", "loopback"}]
            return "UNKNOWN" if names else "DISCONNECTED"
        except OSError:
            return "DISCONNECTED"

    def _gps_status(self) -> str:
        """Report READY only when gpsd exposes a 2D/3D TPV fix.

        A running gpsd daemon is not itself a location fix. gpspipe may emit
        VERSION, DEVICES or TPV mode=1 records while no receiver has a usable
        solution, so FIELD//OS keeps GPS degraded until TPV mode >= 2.
        """
        if shutil.which("gpspipe"):
            output = _run_text(["gpspipe", "-w", "-n", "5"], timeout=2.0)
            saw_tpv = False
            for line in output.splitlines():
                try:
                    record = json.loads(line)
                except (json.JSONDecodeError, TypeError):
                    continue
                if record.get("class") != "TPV":
                    continue
                saw_tpv = True
                try:
                    mode = int(record.get("mode", 0))
                except (TypeError, ValueError):
                    mode = 0
                if mode >= 2:
                    return "READY"
            if output or saw_tpv:
                return "NO FIX"

        if shutil.which("systemctl") and _run_text(["systemctl", "is-active", "gpsd"]) == "active":
            return "NO FIX"
        return "NOT PRESENT"

    def _mesh_status(self) -> str:
        # A working Meshtastic CLI is a strong capability signal and avoids
        # guessing which serial peripheral belongs to the mesh subsystem.
        if shutil.which("meshtastic"):
            return "CLI READY"

        configured = os.environ.get(self.MESH_DEVICE_ENV, "").strip()
        if configured:
            device = Path(configured).expanduser()
            if device.exists():
                return "CONFIGURED"
            return "NOT PRESENT"

        return "NOT PRESENT"


class AutoTelemetryProvider(SystemTelemetryProvider):
    """Production default provider used on both development hosts and RVN-01."""

    pass