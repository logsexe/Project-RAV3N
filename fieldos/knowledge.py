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
        return " ".join(value for value in (self.id, self.title, self.category, self.summary, self.body, self.command or "", self.source, self.path or "") if value).lower()


class KnowledgeIndex:
    """Offline-first, category-aware FIELD//OS knowledge index."""

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
                entries.append(KnowledgeEntry(
                    id=str(item.get("id", "knowledge")), title=str(item.get("title", item.get("id", "Knowledge"))),
                    category=str(item.get("category", "reference")).lower(), summary=str(item.get("summary", "")), body=str(item.get("body", "")),
                    command=(str(item["command"]) if item.get("command") else None), source=str(item.get("source", "FIELD//OS")),
                ))
        raw_paths = os.environ.get("FIELDOS_KNOWLEDGE_PATHS", "")
        for raw in (part for part in raw_paths.split(os.pathsep) if part.strip()):
            entries.extend(cls._index_directory(Path(raw).expanduser()))
        return cls(entries)

    @classmethod
    def _index_directory(cls, root: Path) -> list[KnowledgeEntry]:
        if not root.exists() or not root.is_dir(): return []
        output: list[KnowledgeEntry] = []
        count = 0
        for path in root.rglob("*"):
            if count >= 1500 or not path.is_file() or path.suffix.lower() not in cls.TEXT_SUFFIXES: continue
            try: text = path.read_text(encoding="utf-8", errors="replace")
            except OSError: continue
            if not text.strip(): continue
            relative = path.relative_to(root)
            first_line = next((line.strip("# ") for line in text.splitlines() if line.strip()), path.stem)
            # First directory becomes the human category, so a tree such as
            # ~/knowledge/{medical,radio,navigation,manuals}/... categorises itself.
            category = relative.parts[0].lower() if len(relative.parts) > 1 else root.name.lower()
            output.append(KnowledgeEntry(
                id=f"local:{root.name}:{relative.as_posix()}", title=(first_line[:72] or path.stem), category=category,
                summary=f"Local knowledge // {relative.as_posix()}", body=text[:12000], source=root.name, path=str(path),
            ))
            count += 1
        return output

    @property
    def all(self) -> tuple[KnowledgeEntry, ...]: return tuple(self._entries)

    @property
    def categories(self) -> tuple[str, ...]:
        return tuple(sorted({entry.category for entry in self._entries if entry.category}))

    def for_category(self, category: str) -> list[KnowledgeEntry]:
        wanted = category.lower().strip()
        return sorted((entry for entry in self._entries if entry.category.lower() == wanted), key=lambda entry: entry.title.lower())

    def search(self, query: str, limit: int = 40, category: str | None = None) -> list[KnowledgeEntry]:
        needle = query.lower().strip(); terms = [part for part in needle.split() if part]
        scored: list[tuple[int, KnowledgeEntry]] = []
        for entry in self._entries:
            if category and entry.category.lower() != category.lower().strip(): continue
            haystack = entry.searchable_text
            if terms and not all(term in haystack for term in terms): continue
            score = 1
            for term in terms:
                if term in entry.title.lower(): score += 5
                if term in entry.summary.lower(): score += 2
                score += min(haystack.count(term), 5)
            scored.append((score, entry))
        scored.sort(key=lambda item: (-item[0], item[1].title.lower()))
        return [entry for _, entry in scored[:limit]]

    def context(self, query: str, limit: int = 5, max_chars: int = 10000) -> str:
        chunks: list[str] = []
        used = 0
        for entry in self.search(query, limit=limit):
            chunk = f"[{entry.category.upper()}] {entry.title}\n{entry.summary}\n{entry.body}".strip()
            if used + len(chunk) > max_chars: chunk = chunk[: max(0, max_chars - used)]
            if not chunk: break
            chunks.append(chunk); used += len(chunk)
            if used >= max_chars: break
        return "\n\n---\n\n".join(chunks)
