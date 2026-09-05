from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import json
import os
from pathlib import Path
import re


def _data_root() -> Path:
    override = os.environ.get("FIELDOS_DATA_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".fieldos"


def _safe_id(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", value.strip().upper()).strip("-")
    return cleaned or "FIELD"


@dataclass(slots=True)
class OperationSession:
    id: str
    name: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    notes: list[str] = field(default_factory=list)

    def touch(self) -> None:
        self.updated_at = datetime.now().isoformat(timespec="seconds")


class OperationSessionManager:
    """Persistent FIELD//OS operation/session store.

    Sessions are intentionally simple JSON files so they remain readable and
    recoverable even when FIELD//OS is not running.
    """

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or (_data_root() / "sessions")
        self.root.mkdir(parents=True, exist_ok=True)
        self._sessions: list[OperationSession] = []
        self.active_index = 0
        self._load()
        if not self._sessions:
            self.create("FIELD-001")

    @property
    def sessions(self) -> tuple[OperationSession, ...]:
        return tuple(self._sessions)

    @property
    def active(self) -> OperationSession:
        return self._sessions[self.active_index]

    def create(self, name: str | None = None) -> OperationSession:
        if not name:
            name = f"FIELD-{len(self._sessions) + 1:03d}"
        base = _safe_id(name)
        candidate = base
        suffix = 2
        existing = {item.id for item in self._sessions}
        while candidate in existing:
            candidate = f"{base}-{suffix:02d}"
            suffix += 1
        session = OperationSession(id=candidate, name=name.strip() or candidate)
        self._sessions.append(session)
        self.active_index = len(self._sessions) - 1
        self._save(session)
        self._ensure_dirs(session)
        return session

    def select(self, index: int) -> OperationSession:
        self.active_index = max(0, min(index, len(self._sessions) - 1))
        return self.active

    def add_note(self, text: str) -> None:
        text = text.strip()
        if not text:
            return
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.active.notes.append(f"[{stamp}] {text}")
        self.active.touch()
        self._save(self.active)

    def session_path(self, session: OperationSession | None = None) -> Path:
        item = session or self.active
        return self.root / item.id

    def _ensure_dirs(self, session: OperationSession) -> None:
        base = self.session_path(session)
        for child in ("notes", "scans", "captures", "evidence", "exports"):
            (base / child).mkdir(parents=True, exist_ok=True)

    def _save(self, session: OperationSession) -> None:
        self._ensure_dirs(session)
        path = self.session_path(session) / "metadata.json"
        payload = {
            "id": session.id,
            "name": session.name,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "notes": session.notes,
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        notes_path = self.session_path(session) / "notes" / "timeline.txt"
        notes_path.write_text("\n".join(session.notes) + ("\n" if session.notes else ""), encoding="utf-8")

    def _load(self) -> None:
        loaded: list[OperationSession] = []
        for metadata in sorted(self.root.glob("*/metadata.json")):
            try:
                payload = json.loads(metadata.read_text(encoding="utf-8"))
                loaded.append(
                    OperationSession(
                        id=str(payload["id"]),
                        name=str(payload.get("name", payload["id"])),
                        created_at=str(payload.get("created_at", "")),
                        updated_at=str(payload.get("updated_at", "")),
                        notes=[str(item) for item in payload.get("notes", [])],
                    )
                )
            except (OSError, ValueError, KeyError, TypeError):
                continue
        self._sessions = loaded
