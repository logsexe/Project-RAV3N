from __future__ import annotations

from dataclasses import dataclass
import platform
import shutil
import subprocess


@dataclass(frozen=True, slots=True)
class AirgapStatus:
    supported: bool
    active: bool
    detail: str


class AirgapController:
    """Best-effort Linux radio/network isolation controller."""

    def status(self) -> AirgapStatus:
        if platform.system() != "Linux":
            return AirgapStatus(False, False, "Linux only")
        if shutil.which("nmcli"):
            result = subprocess.run(["nmcli", "networking", "connectivity"], capture_output=True, text=True, timeout=5, check=False)
            active = result.stdout.strip().lower() == "none"
            return AirgapStatus(True, active, f"nmcli connectivity={result.stdout.strip() or 'unknown'}")
        if shutil.which("rfkill"):
            result = subprocess.run(["rfkill", "list"], capture_output=True, text=True, timeout=5, check=False)
            return AirgapStatus(True, "soft blocked: yes" in result.stdout.lower(), "rfkill radio state")
        return AirgapStatus(False, False, "nmcli/rfkill unavailable")

    def enable(self, *, confirm: bool = False) -> AirgapStatus:
        if not confirm:
            raise PermissionError("Air-gap activation requires explicit confirmation")
        return self._apply(True)

    def disable(self, *, confirm: bool = False) -> AirgapStatus:
        if not confirm:
            raise PermissionError("Air-gap deactivation requires explicit confirmation")
        return self._apply(False)

    def _apply(self, enabled: bool) -> AirgapStatus:
        if platform.system() != "Linux":
            return AirgapStatus(False, False, "Linux only")
        actions: list[list[str]] = []
        if enabled:
            if shutil.which("nmcli"):
                actions.append(["nmcli", "networking", "off"])
            if shutil.which("rfkill"):
                actions.extend([["rfkill", "block", "wifi"], ["rfkill", "block", "bluetooth"]])
        else:
            if shutil.which("rfkill"):
                actions.extend([["rfkill", "unblock", "wifi"], ["rfkill", "unblock", "bluetooth"]])
            if shutil.which("nmcli"):
                actions.append(["nmcli", "networking", "on"])
        if not actions:
            return AirgapStatus(False, False, "nmcli/rfkill unavailable")
        errors = []
        for command in actions:
            result = subprocess.run(command, capture_output=True, text=True, timeout=10, check=False)
            if result.returncode:
                errors.append((result.stderr or result.stdout).strip() or "command failed")
        if errors:
            return AirgapStatus(True, not enabled, "; ".join(errors))
        return AirgapStatus(True, enabled, "networking and local radios disabled" if enabled else "networking and local radios enabled")
