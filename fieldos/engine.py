from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import mimetypes
from pathlib import Path
import shutil
import sqlite3
import uuid

from fieldos.operations import _data_root
from fieldos.vault import Vault


@dataclass(frozen=True, slots=True)
class Asset:
    id: str
    operation_id: str
    kind: str
    value: str
    label: str
    created_at: str
    updated_at: str
    metadata: dict


@dataclass(frozen=True, slots=True)
class Evidence:
    id: str
    operation_id: str
    source_name: str
    stored_path: str
    sha256: str
    size: int
    mime: str
    created_at: str
    encrypted: bool
    asset_id: str | None
    metadata: dict


@dataclass(frozen=True, slots=True)
class Event:
    id: int
    operation_id: str
    timestamp: str
    event_type: str
    summary: str
    asset_id: str | None
    evidence_id: str | None
    metadata: dict


class OperationsEngine:
    """Structured asset, evidence and timeline engine for FIELD//OS."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or _data_root()
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "operations.db"
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.db_path)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        return db

    def _init_db(self) -> None:
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS assets (
                    id TEXT PRIMARY KEY, operation_id TEXT NOT NULL, kind TEXT NOT NULL,
                    value TEXT NOT NULL, label TEXT NOT NULL, created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL, metadata TEXT NOT NULL DEFAULT '{}',
                    UNIQUE(operation_id, kind, value)
                );
                CREATE TABLE IF NOT EXISTS evidence (
                    id TEXT PRIMARY KEY, operation_id TEXT NOT NULL, source_name TEXT NOT NULL,
                    stored_path TEXT NOT NULL, sha256 TEXT NOT NULL, size INTEGER NOT NULL,
                    mime TEXT NOT NULL, created_at TEXT NOT NULL, encrypted INTEGER NOT NULL DEFAULT 0,
                    asset_id TEXT, metadata TEXT NOT NULL DEFAULT '{}'
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, operation_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL, event_type TEXT NOT NULL, summary TEXT NOT NULL,
                    asset_id TEXT, evidence_id TEXT, metadata TEXT NOT NULL DEFAULT '{}'
                );
                CREATE INDEX IF NOT EXISTS idx_assets_operation ON assets(operation_id);
                CREATE INDEX IF NOT EXISTS idx_evidence_operation ON evidence(operation_id);
                CREATE INDEX IF NOT EXISTS idx_events_operation ON events(operation_id, timestamp);
            """)

    def upsert_asset(self, operation_id: str, kind: str, value: str, *, label: str = "", metadata: dict | None = None) -> Asset:
        now = datetime.now().isoformat(timespec="seconds")
        kind = kind.strip().upper() or "UNKNOWN"
        value = value.strip()
        if not value:
            raise ValueError("Asset value is required")
        metadata = metadata or {}
        with self._connect() as db:
            row = db.execute("SELECT id, created_at FROM assets WHERE operation_id=? AND kind=? AND value=?", (operation_id, kind, value)).fetchone()
            if row:
                asset_id, created_at = row["id"], row["created_at"]
                db.execute("UPDATE assets SET label=?, updated_at=?, metadata=? WHERE id=?", (label.strip() or value, now, json.dumps(metadata), asset_id))
            else:
                asset_id = f"AS-{uuid.uuid4().hex[:8].upper()}"
                created_at = now
                db.execute("INSERT INTO assets VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (asset_id, operation_id, kind, value, label.strip() or value, now, now, json.dumps(metadata)))
        self.record_event(operation_id, "ASSET", f"{kind} {value}", asset_id=asset_id, metadata=metadata)
        return Asset(asset_id, operation_id, kind, value, label.strip() or value, created_at, now, metadata)

    def list_assets(self, operation_id: str) -> list[Asset]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM assets WHERE operation_id=? ORDER BY updated_at DESC", (operation_id,)).fetchall()
        return [Asset(row["id"], row["operation_id"], row["kind"], row["value"], row["label"], row["created_at"], row["updated_at"], json.loads(row["metadata"] or "{}")) for row in rows]

    def ingest_evidence(self, operation_id: str, source: Path, *, operation_path: Path | None = None, asset_id: str | None = None, metadata: dict | None = None, vault: Vault | None = None) -> Evidence:
        source = source.expanduser().resolve()
        if not source.is_file():
            raise FileNotFoundError(source)
        data = source.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        size = len(data)
        mime = mimetypes.guess_type(source.name)[0] or "application/octet-stream"
        metadata = metadata or {}
        evidence_id = f"EV-{uuid.uuid4().hex[:8].upper()}"
        base = operation_path or (self.root / "sessions" / operation_id)
        evidence_dir = base / "evidence"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        stored_name = f"{evidence_id}-{source.name}" + (".rvn" if vault else "")
        destination = evidence_dir / stored_name
        if vault:
            destination.write_bytes(vault.encrypt_bytes(data))
        else:
            shutil.copy2(source, destination)
        now = datetime.now().isoformat(timespec="seconds")
        with self._connect() as db:
            db.execute("INSERT INTO evidence VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (evidence_id, operation_id, source.name, str(destination), digest, size, mime, now, int(vault is not None), asset_id, json.dumps(metadata)))
        self.record_event(operation_id, "EVIDENCE", f"{evidence_id} {source.name}", asset_id=asset_id, evidence_id=evidence_id, metadata={"sha256": digest, "encrypted": vault is not None, **metadata})
        return Evidence(evidence_id, operation_id, source.name, str(destination), digest, size, mime, now, vault is not None, asset_id, metadata)

    def list_evidence(self, operation_id: str) -> list[Evidence]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM evidence WHERE operation_id=? ORDER BY created_at DESC", (operation_id,)).fetchall()
        return [Evidence(row["id"], row["operation_id"], row["source_name"], row["stored_path"], row["sha256"], row["size"], row["mime"], row["created_at"], bool(row["encrypted"]), row["asset_id"], json.loads(row["metadata"] or "{}")) for row in rows]

    def verify_evidence(self, evidence_id: str, *, vault: Vault | None = None) -> bool:
        with self._connect() as db:
            row = db.execute("SELECT * FROM evidence WHERE id=?", (evidence_id,)).fetchone()
        if row is None:
            raise KeyError(evidence_id)
        payload = Path(row["stored_path"]).read_bytes()
        if bool(row["encrypted"]):
            if vault is None:
                raise PermissionError("Encrypted evidence requires an unlocked vault")
            payload = vault.decrypt_bytes(payload)
        return hashlib.sha256(payload).hexdigest() == row["sha256"]

    def record_event(self, operation_id: str, event_type: str, summary: str, *, asset_id: str | None = None, evidence_id: str | None = None, metadata: dict | None = None) -> int:
        now = datetime.now().isoformat(timespec="seconds")
        with self._connect() as db:
            cursor = db.execute("INSERT INTO events(operation_id,timestamp,event_type,summary,asset_id,evidence_id,metadata) VALUES(?,?,?,?,?,?,?)", (operation_id, now, event_type.upper(), summary, asset_id, evidence_id, json.dumps(metadata or {})))
            return int(cursor.lastrowid)

    def timeline(self, operation_id: str, *, limit: int = 100) -> list[Event]:
        with self._connect() as db:
            rows = db.execute("SELECT * FROM events WHERE operation_id=? ORDER BY id DESC LIMIT ?", (operation_id, int(limit))).fetchall()
        return [Event(row["id"], row["operation_id"], row["timestamp"], row["event_type"], row["summary"], row["asset_id"], row["evidence_id"], json.loads(row["metadata"] or "{}")) for row in rows]
