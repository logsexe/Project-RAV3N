from __future__ import annotations

from dataclasses import dataclass
import html as html_lib
import importlib.util
import os
import re
from pathlib import Path
from typing import Any

import yaml

from .live_services import zim_files

# Best-effort keyword -> KNOWLEDGE_SECTIONS category mapping for ZIM archives,
# derived from the archive's filename since a ZIM file has no notion of the
# local category tree local text files get from their directory name (see
# _index_directory below). Falls back to "reference" (the GENERAL section)
# when nothing matches. Kept in sync with qt_v3_app.KNOWLEDGE_SECTIONS.
_ZIM_CATEGORY_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("medical", "medical"), ("first-aid", "medical"), ("first_aid", "medical"), ("firstaid", "medical"),
    ("survival", "survival"),
    ("radio", "radio"), ("ham", "radio"),
    ("navigat", "navigation"), ("map", "navigation"),
    ("repair", "repair"), ("maint", "repair"),
    ("travel", "travel"),
    ("emergency", "emergency"), ("preparedness", "emergency"),
    ("secur", "cyber"), ("hack", "cyber"), ("cyber", "cyber"), ("forensic", "cyber"),
    ("linux", "computing"), ("comput", "computing"), ("utilit", "computing"),
    ("mesh", "comms"), ("comms", "comms"), ("communicat", "comms"),
)

_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"[ \t]+")


def _zim_category(stem: str) -> str:
    lowered = stem.lower()
    for needle, category in _ZIM_CATEGORY_KEYWORDS:
        if needle in lowered:
            return category
    return "reference"


def _html_to_text(raw: str) -> str:
    """Strip markup from a ZIM article so it reads in a plain QTextEdit.

    ZIM articles (Wikipedia dumps etc.) are almost always HTML. We don't
    pull in an HTML parser dependency for this -- a tag-stripping regex plus
    entity-unescaping is good enough for offline field reference text.
    """
    text = _TAG_RE.sub(" ", raw)
    text = html_lib.unescape(text)
    text = _WHITESPACE_RE.sub(" ", text)
    lines = (line.strip() for line in text.splitlines())
    return "\n".join(line for line in lines if line).strip()


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
    # Set only for entries backed by a .zim archive entry. When both are set,
    # `body` is deliberately left "" at index time -- see KnowledgeIndex.body_for().
    zim_source: str | None = None
    zim_entry_path: str | None = None

    @property
    def searchable_text(self) -> str:
        return " ".join(value for value in (self.id, self.title, self.category, self.summary, self.body, self.command or "", self.source, self.path or "") if value).lower()

    @property
    def is_zim(self) -> bool:
        return self.zim_source is not None and self.zim_entry_path is not None


class KnowledgeIndex:
    """Offline-first, category-aware FIELD//OS knowledge index."""

    TEXT_SUFFIXES = {".md", ".txt", ".rst", ".yaml", ".yml", ".json"}

    def __init__(self, entries: list[KnowledgeEntry], zim_archives: dict[str, Any] | None = None) -> None:
        self._entries = entries
        # path (str) -> opened libzim.reader.Archive. Archives are opened once
        # up front (cheap: reads the directory/header, not article bodies) and
        # reused for every search and every lazy body fetch.
        self._zim_archives: dict[str, Any] = zim_archives or {}
        self._zim_body_cache: dict[str, str] = {}

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
        return cls(entries, cls._open_zim_archives())

    @classmethod
    def _open_zim_archives(cls) -> dict[str, Any]:
        """Open every discovered .zim archive, or return {} if unavailable.

        Fails closed exactly like fieldos.live_services.system_metrics() /
        meshtastic_nodes(): a missing `libzim` package, a broken install, or
        a corrupt/unreadable individual .zim file all degrade to "no ZIM
        entries" rather than raising anywhere in LIBRARY.
        """
        if importlib.util.find_spec("libzim") is None:
            return {}
        try:
            from libzim.reader import Archive
        except Exception:
            return {}
        try:
            paths = zim_files()
        except Exception:
            return {}
        archives: dict[str, Any] = {}
        for path in paths:
            try:
                archives[str(path)] = Archive(str(path))
            except Exception:
                continue
        return archives

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
    def zim_archive_count(self) -> int:
        return len(self._zim_archives)

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
        # ZIM archives are only ever consulted for a real query -- an empty
        # search box means "browse everything local", and running a
        # full-archive query against a multi-gigabyte ZIM for that would be
        # both slow and a poor match for "browse" semantics anyway.
        if needle and self._zim_archives:
            for rank, entry in enumerate(self._search_zim(needle, limit)):
                if category and entry.category.lower() != category.lower().strip(): continue
                scored.append((max(1, 6 - rank), entry))
        scored.sort(key=lambda item: (-item[0], item[1].title.lower()))
        return [entry for _, entry in scored[:limit]]

    def _search_zim(self, query: str, limit: int) -> list[KnowledgeEntry]:
        """Run libzim's native full-text Searcher against every open archive.

        Only lightweight metadata (title, category, the archive path and the
        in-archive entry path) is materialised here -- never the article
        body. Nothing in this codebase iterates a ZIM archive's entries in
        Python; libzim's Xapian-backed Searcher does the actual matching.
        """
        if importlib.util.find_spec("libzim") is None or not self._zim_archives:
            return []
        try:
            from libzim.search import Query, Searcher
        except Exception:
            return []
        per_archive = max(1, min(limit, 25))
        results: list[KnowledgeEntry] = []
        for zim_path, archive in self._zim_archives.items():
            try:
                search = Searcher(archive).search(Query().set_query(query))
                hit_paths = list(search.getResults(0, per_archive))
            except Exception:
                continue
            stem = Path(zim_path).stem
            category = _zim_category(stem)
            for entry_path in hit_paths:
                try:
                    zim_entry = archive.get_entry_by_path(entry_path)
                    if zim_entry.is_redirect:
                        zim_entry = zim_entry.get_redirect_entry()
                    title = zim_entry.title or entry_path
                    real_path = zim_entry.path
                except Exception:
                    continue
                results.append(KnowledgeEntry(
                    id=f"zim:{zim_path}:{real_path}", title=title, category=category,
                    summary=f"ZIM ARCHIVE // {stem}", source=stem,
                    zim_source=zim_path, zim_entry_path=real_path,
                ))
        return results[:limit]

    def body_for(self, entry: KnowledgeEntry) -> str:
        """Return an entry's full body, fetching it from its .zim archive on
        first access. Local/bundled entries already carry their body eagerly
        and are returned as-is. Results are cached per (archive, path) so
        re-opening the same article doesn't re-read it from the archive.
        """
        if entry.body or not entry.is_zim:
            return entry.body
        cache_key = f"{entry.zim_source}\x1f{entry.zim_entry_path}"
        if cache_key in self._zim_body_cache:
            return self._zim_body_cache[cache_key]
        text = ""
        archive = self._zim_archives.get(entry.zim_source)
        if archive is not None:
            try:
                zim_entry = archive.get_entry_by_path(entry.zim_entry_path)
                if zim_entry.is_redirect:
                    zim_entry = zim_entry.get_redirect_entry()
                item = zim_entry.get_item()
                raw = bytes(item.content).decode("utf-8", errors="replace")
                text = _html_to_text(raw) if "html" in (item.mimetype or "") else raw
                text = text[:12000]
            except Exception:
                text = ""
        self._zim_body_cache[cache_key] = text
        return text

    def context(self, query: str, limit: int = 5, max_chars: int = 10000) -> str:
        chunks: list[str] = []
        used = 0
        for entry in self.search(query, limit=limit):
            body = self.body_for(entry)
            chunk = f"[{entry.category.upper()}] {entry.title}\n{entry.summary}\n{body}".strip()
            if used + len(chunk) > max_chars: chunk = chunk[: max(0, max_chars - used)]
            if not chunk: break
            chunks.append(chunk); used += len(chunk)
            if used >= max_chars: break
        return "\n\n---\n\n".join(chunks)
