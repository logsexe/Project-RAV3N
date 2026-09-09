from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(slots=True, frozen=True)
class PlaybookStep:
    name: str
    description: str = ""
    tool: str | None = None
    command: str | None = None


@dataclass(slots=True, frozen=True)
class Playbook:
    id: str
    name: str
    category: str
    description: str = ""
    steps: tuple[PlaybookStep, ...] = ()


class PlaybookIndex:
    def __init__(self, playbooks: list[Playbook]) -> None:
        self._playbooks = playbooks

    @classmethod
    def load_default(cls) -> "PlaybookIndex":
        project_root = Path(__file__).resolve().parents[1]
        manifest_dir = project_root / "config" / "playbooks"
        if not manifest_dir.exists():
            return cls([])

        playbooks_by_id: dict[str, Playbook] = {}
        for path in sorted(manifest_dir.glob("*.yaml")):
            with path.open("r", encoding="utf-8") as handle:
                payload = yaml.safe_load(handle) or {}
            for item in payload.get("playbooks", []):
                steps = tuple(
                    PlaybookStep(
                        name=str(step.get("name", "Step")),
                        description=str(step.get("description", "")),
                        tool=(str(step["tool"]) if step.get("tool") else None),
                        command=(str(step["command"]) if step.get("command") else None),
                    )
                    for step in item.get("steps", [])
                )
                playbook = Playbook(
                    id=str(item.get("id", "playbook")),
                    name=str(item.get("name", item.get("id", "Playbook"))),
                    category=str(item.get("category", "field")),
                    description=str(item.get("description", "")),
                    steps=steps,
                )
                playbooks_by_id[playbook.id] = playbook
        return cls(list(playbooks_by_id.values()))

    @property
    def all(self) -> tuple[Playbook, ...]:
        return tuple(self._playbooks)
