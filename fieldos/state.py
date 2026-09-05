from __future__ import annotations

import json
import os
from pathlib import Path


def _data_root() -> Path:
    override = os.environ.get("FIELDOS_DATA_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".fieldos"


class OperatorState:
    """Small persistent operator state store for favourites and recents."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or (_data_root() / "state.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.favourites: list[str] = []
        self.recent_tools: list[str] = []
        self._load()

    def is_favourite(self, tool_id: str) -> bool:
        return tool_id in self.favourites

    def toggle_favourite(self, tool_id: str) -> bool:
        if tool_id in self.favourites:
            self.favourites.remove(tool_id)
            enabled = False
        else:
            self.favourites.append(tool_id)
            enabled = True
        self._save()
        return enabled

    def record_recent(self, tool_id: str) -> None:
        if tool_id in self.recent_tools:
            self.recent_tools.remove(tool_id)
        self.recent_tools.insert(0, tool_id)
        del self.recent_tools[20:]
        self._save()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            self.favourites = [str(item) for item in payload.get("favourites", [])]
            self.recent_tools = [str(item) for item in payload.get("recent_tools", [])]
        except (OSError, ValueError, TypeError):
            self.favourites = []
            self.recent_tools = []

    def _save(self) -> None:
        payload = {
            "favourites": self.favourites,
            "recent_tools": self.recent_tools,
        }
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
