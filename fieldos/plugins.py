from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(slots=True, frozen=True)
class PluginRecord:
    id: str
    name: str
    category: str
    version: str
    platform: str
    requires: tuple[str, ...]
    privilege: str
    network: str
    hardware: str
    execution: str
    enabled: bool
    description: str = ""


class PluginRegistry:
    """Metadata-only FIELD//OS plugin registry for V1.5.

    V1.5 does not import or execute arbitrary plugin Python code. The registry
    exposes declared capabilities and an in-memory enable/disable state so an
    operator can inspect integrations before any later execution framework is
    introduced.
    """

    def __init__(self, plugins: list[PluginRecord]) -> None:
        self._plugins = plugins

    @classmethod
    def load_default(cls) -> "PluginRegistry":
        root = Path(__file__).resolve().parents[1] / "config" / "plugins"
        plugins: list[PluginRecord] = []
        if not root.exists():
            return cls(plugins)
        for path in sorted(root.glob("*.yaml")):
            with path.open("r", encoding="utf-8") as handle:
                payload = yaml.safe_load(handle) or {}
            for item in payload.get("plugins", []):
                plugins.append(
                    PluginRecord(
                        id=str(item.get("id", "unknown")),
                        name=str(item.get("name", item.get("id", "UNKNOWN"))),
                        category=str(item.get("category", "utilities")),
                        version=str(item.get("version", "0.0")),
                        platform=str(item.get("platform", "any")),
                        requires=tuple(str(v) for v in item.get("requires", [])),
                        privilege=str(item.get("privilege", "user")),
                        network=str(item.get("network", "optional")),
                        hardware=str(item.get("hardware", "none")),
                        execution=str(item.get("execution", "manual")),
                        enabled=bool(item.get("enabled", True)),
                        description=str(item.get("description", "")),
                    )
                )
        return cls(plugins)

    @property
    def all(self) -> tuple[PluginRecord, ...]:
        return tuple(self._plugins)

    def enabled_count(self) -> int:
        return sum(1 for plugin in self._plugins if plugin.enabled)

    def toggle(self, index: int) -> PluginRecord:
        current = self._plugins[index]
        updated = PluginRecord(
            id=current.id,
            name=current.name,
            category=current.category,
            version=current.version,
            platform=current.platform,
            requires=current.requires,
            privilege=current.privilege,
            network=current.network,
            hardware=current.hardware,
            execution=current.execution,
            enabled=not current.enabled,
            description=current.description,
        )
        self._plugins[index] = updated
        return updated
