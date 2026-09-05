from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

import yaml


@dataclass(slots=True, frozen=True)
class KnowledgeEntry:
    id: str
    title: str
    category: str
    summary: str = ""
    body: str = ""
    command: str | None = None
    source: str = "FIELD//OS"
    path: str | None = None

    @property
    def searchable_text(self) -> str:
        return " ".join(
            value
            for value in (
                self.id,
                self.title,
                self.category,
                self.summary,
                self.body,
                self.command or "",
                self.source,
                self.path or "",
            )
            if value
        ).lower()


class KnowledgeIndex:
    """Offline-first knowledge index.

    Bundled reference records are loaded from config/knowledge/core.yaml. Optional
    local repositories or documentation trees can be indexed by setting
    FIELDOS_KNOWLEDGE_PATHS to an os.pathsep-separated list of directories.
    This is intended for local copies of resources such as SquidSec CyberDeck,
    BlueTeam-Tools, RedTeam-Tools and operator-authored notes.
    """

    TEXT_SUFFIXES = {".md", ".txt", ".rst", ".yaml", ".yml", ".json"}

    def __init__(self, entries: list[KnowledgeEntry]) -> None:
        self._entries = entries

    @classmethod
    def load_default(cls) -> "KnowledgeIndex":
        project_root = Path(__file__).resolve().parents[1]
        entries: list[KnowledgeEntry] = []
        bundled = project_root / "config" / "knowledge" / "core.yaml"
        if bundled.exists():
            with bundled.open("r", encoding="utf-8") as handle:
                payload = yaml.safe_load(handle) or {}
            for item in payload.get("entries", []):
                entries.append(
                    KnowledgeEntry(
                        id=str(item.get("id", "knowledge")),
                        title=str(item.get("title", item.get("id", "Knowledge"))),
                        category=str(item.get("category", "reference")),
                        summary=str(item.get("summary", "")),
                        body=str(item.get("body", "")),
                        command=(str(item["command"]) if item.get("command") else None),
                        source=str(item.get("source", "FIELD//OS")),
                    )
                )

        raw_paths = os.environ.get("FIELDOS_KNOWLEDGE_PATHS", "")
        for raw in (part for part in raw_paths.split(os.pathsep) if part.strip()):
            entries.extend(cls._index_directory(Path(raw).expanduser()))
        return cls(entries)

    @classmethod
    def _index_directory(cls, root: Path) -> list[KnowledgeEntry]:
        if not root.exists() or not root.is_dir():
            return []
        output: list[KnowledgeEntry] = []
        count = 0
        for path in root.rglob("*"):
            if count >= 1500 or not path.is_file() or path.suffix.lower() not in cls.TEXT_SUFFIXES:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if not text.strip():
                continue
            relative = path.relative_to(root)
            first_line = next((line.strip("# ") for line in text.splitlines() if line.strip()), path.stem)
            title = first_line[:72] or path.stem
            body = text[:12000]
            output.append(
                KnowledgeEntry(
                    id=f"local:{root.name}:{relative.as_posix()}",
                    title=title,
                    category="local",
                    summary=f"Local knowledge file // {relative.as_posix()}",
                    body=body,
                    source=root.name,
                    path=str(path),
                )
            )
            count += 1
        return output

    @property
    def all(self) -> tuple[KnowledgeEntry, ...]:
        return tuple(self._entries)

    def search(self, query: str, limit: int = 40) -> list[KnowledgeEntry]:
        needle = query.lower().strip()
        if not needle:
            return []
        terms = [part for part in needle.split() if part]
        scored: list[tuple[int, KnowledgeEntry]] = []
        for entry in self._entries:
            haystack = entry.searchable_text
            if not all(term in haystack for term in terms):
                continue
            score = 0
            title = entry.title.lower()
            summary = entry.summary.lower()
            for term in terms:
                if term in title:
                    score += 5
                if term in summary:
                    score += 2
                score += min(haystack.count(term), 5)
            scored.append((score, entry))
        scored.sort(key=lambda item: (-item[0], item[1].title.lower()))
        return [entry for _, entry in scored[:limit]]
