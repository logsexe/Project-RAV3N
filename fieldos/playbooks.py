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
        path = project_root / "config" / "playbooks" / "core.yaml"
        if not path.exists():
            return cls([])
        with path.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}
        playbooks: list[Playbook] = []
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
            playbooks.append(
                Playbook(
                    id=str(item.get("id", "playbook")),
                    name=str(item.get("name", item.get("id", "Playbook"))),
                    category=str(item.get("category", "field")),
                    description=str(item.get("description", "")),
                    steps=steps,
                )
            )
        return cls(playbooks)

    @property
    def all(self) -> tuple[Playbook, ...]:
        return tuple(self._playbooks)
