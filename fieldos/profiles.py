from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from fieldos.operations import _data_root


@dataclass(frozen=True, slots=True)
class Profile:
    name: str
    description: str
    categories: tuple[str, ...] | None
    network_policy: str
    hardware_policy: str
    low_power: bool = False
    offline_only: bool = False


PROFILES = (
    Profile("FIELD", "General field operations", None, "NORMAL", "NORMAL"),
    Profile("BLUE", "Defensive security and incident response", ("BLUE", "OSINT", "NETWORK", "FORENSICS", "FIELD", "COMMS", "HARDWARE", "RF", "UTILITIES"), "NORMAL", "NORMAL"),
    Profile("RED", "Authorised offensive security operations", ("RED", "OSINT", "NETWORK", "FIELD", "COMMS", "HARDWARE", "RF", "UTILITIES"), "NORMAL", "NORMAL"),
    Profile("OSINT", "Open-source intelligence and enrichment", ("OSINT", "NETWORK", "FIELD", "UTILITIES"), "NORMAL", "NORMAL"),
    Profile("FORENSICS", "Evidence handling and offline analysis", ("FORENSICS", "BLUE", "FIELD", "HARDWARE", "UTILITIES"), "RESTRICTED", "EVIDENCE"),
    Profile("RF", "Radio-frequency observation and analysis", ("RF", "COMMS", "FIELD", "HARDWARE", "UTILITIES"), "NORMAL", "RF"),
    Profile("AIRGAP", "Network-isolated evidence and analysis mode", ("FORENSICS", "BLUE", "OSINT", "FIELD", "HARDWARE", "UTILITIES"), "AIRGAP", "EVIDENCE", offline_only=True),
    Profile("LOW POWER", "Reduced hardware and background activity", ("FIELD", "COMMS", "HARDWARE", "UTILITIES"), "LIMITED", "LOW_POWER", low_power=True),
)


class ProfileManager:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (_data_root() / "profile.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._profile = PROFILES[0]
        self._load()

    @property
    def current(self) -> Profile:
        return self._profile

    def set(self, name: str) -> Profile:
        wanted = name.strip().upper().replace("_", " ")
        for profile in PROFILES:
            if profile.name == wanted:
                self._profile = profile
                self._save()
                return profile
        raise ValueError(f"Unknown FIELD//OS profile: {name}")

    def next(self) -> Profile:
        index = PROFILES.index(self._profile)
        self._profile = PROFILES[(index + 1) % len(PROFILES)]
        self._save()
        return self._profile

    def allows_tool(self, tool) -> bool:
        if self._profile.offline_only and not bool(getattr(tool, "offline", False)):
            return False
        if self._profile.categories is None:
            return True
        return str(getattr(tool, "category", "")).upper() in self._profile.categories

    def filter_tools(self, tools) -> tuple:
        return tuple(tool for tool in tools if self.allows_tool(tool))

    def _save(self) -> None:
        self.path.write_text(json.dumps({"profile": self._profile.name}, indent=2), encoding="utf-8")

    def _load(self) -> None:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            self.set(str(payload.get("profile", "FIELD")))
        except (OSError, ValueError, TypeError):
            self._profile = PROFILES[0]
