from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil

import yaml


@dataclass(slots=True, frozen=True)
class ToolRecipe:
    name: str
    command: str
    description: str = ""


@dataclass(slots=True, frozen=True)
class ToolRecord:
    id: str
    name: str
    category: str
    priority: str = "optional"
    subcategory: str | None = None
    description: str = ""
    command: str | None = None
    docs: str | None = None
    offline: bool = False
    authorised_use_only: bool = False
    requires_root: bool = False
    platforms: tuple[str, ...] = ()
    recipes: tuple[ToolRecipe, ...] = ()

    @property
    def installed(self) -> bool:
        if not self.command:
            return False
        executable = self.command.split()[0]
        return shutil.which(executable) is not None


class ToolIndex:
    """Load and query FIELD//OS tool manifests."""

    def __init__(self, tools: list[ToolRecord]) -> None:
        self._tools = tools

    @classmethod
    def load_default(cls) -> "ToolIndex":
        project_root = Path(__file__).resolve().parents[1]
        manifest_path = project_root / "config" / "tools" / "core.yaml"

        if not manifest_path.exists():
            return cls([])

        with manifest_path.open("r", encoding="utf-8") as handle:
            payload = yaml.safe_load(handle) or {}

        tools: list[ToolRecord] = []
        for item in payload.get("tools", []):
            recipes = tuple(
                ToolRecipe(
                    name=str(recipe.get("name", "Recipe")),
                    command=str(recipe.get("command", "")),
                    description=str(recipe.get("description", "")),
                )
                for recipe in item.get("recipes", [])
                if recipe.get("command")
            )
            tools.append(
                ToolRecord(
                    id=str(item.get("id", "unknown")),
                    name=str(item.get("name", item.get("id", "UNKNOWN"))),
                    category=str(item.get("category", "utilities")).lower(),
                    priority=str(item.get("priority", "optional")),
                    subcategory=(
                        str(item["subcategory"])
                        if item.get("subcategory") is not None
                        else None
                    ),
                    description=str(item.get("description", "")),
                    command=(str(item["command"]) if item.get("command") else None),
                    docs=(str(item["docs"]) if item.get("docs") else None),
                    offline=bool(item.get("offline", False)),
                    authorised_use_only=bool(item.get("authorised_use_only", False)),
                    requires_root=bool(item.get("requires_root", False)),
                    platforms=tuple(str(value) for value in item.get("platforms", [])),
                    recipes=recipes,
                )
            )

        return cls(tools)

    @property
    def all(self) -> tuple[ToolRecord, ...]:
        return tuple(self._tools)

    def for_category(self, category: str) -> list[ToolRecord]:
        category = category.lower().strip()
        return sorted(
            [tool for tool in self._tools if tool.category == category],
            key=lambda tool: (self._priority_rank(tool.priority), tool.name.lower()),
        )

    def search(self, query: str) -> list[ToolRecord]:
        needle = query.lower().strip()
        if not needle:
            return []

        matches = []
        for tool in self._tools:
            recipe_text = " ".join(
                f"{recipe.name} {recipe.description} {recipe.command}"
                for recipe in tool.recipes
            )
            haystack = " ".join(
                value
                for value in [
                    tool.id,
                    tool.name,
                    tool.category,
                    tool.subcategory or "",
                    tool.priority,
                    tool.description,
                    recipe_text,
                ]
                if value
            ).lower()
            if needle in haystack:
                matches.append(tool)

        return sorted(
            matches,
            key=lambda tool: (self._priority_rank(tool.priority), tool.name.lower()),
        )

    def installed_count(self) -> int:
        return sum(1 for tool in self._tools if tool.installed)

    @staticmethod
    def _priority_rank(priority: str) -> int:
        order = {
            "core": 0,
            "recommended": 1,
            "planned": 2,
            "optional": 3,
        }
        return order.get(priority.lower(), 99)
