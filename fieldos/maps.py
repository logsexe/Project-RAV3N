from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import json
from pathlib import Path
import sqlite3

from fieldos.operations import _data_root


@dataclass(slots=True)
class Waypoint:
    id: str
    latitude: float
    longitude: float
    label: str
    created_at: str
    operation_id: str = ""


@dataclass(slots=True)
class MeshNode:
    id: str
    latitude: float
    longitude: float
    label: str
    last_heard: str


class OfflineMapStore:
    """Offline MBTiles catalogue plus waypoint/Meshtastic overlays."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or (_data_root() / "maps")
        self.root.mkdir(parents=True, exist_ok=True)
        self.waypoints_path = self.root / "waypoints.json"
        self.mesh_path = self.root / "mesh_nodes.json"

    def maps(self) -> tuple[Path, ...]:
        return tuple(sorted(self.root.glob("*.mbtiles")))

    def metadata(self, map_path: Path) -> dict[str, str]:
        with sqlite3.connect(map_path) as db:
            rows = db.execute("SELECT name, value FROM metadata").fetchall()
        return {str(name): str(value) for name, value in rows}

    def get_tile(self, map_path: Path, zoom: int, x: int, y_xyz: int) -> bytes | None:
        y_tms = (1 << zoom) - 1 - y_xyz
        with sqlite3.connect(map_path) as db:
            row = db.execute("SELECT tile_data FROM tiles WHERE zoom_level=? AND tile_column=? AND tile_row=?", (zoom, x, y_tms)).fetchone()
        return bytes(row[0]) if row else None

    def add_waypoint(self, latitude: float, longitude: float, label: str, operation_id: str = "") -> Waypoint:
        items = self.waypoints()
        item = Waypoint(f"WP-{len(items)+1:04d}", float(latitude), float(longitude), label.strip() or "WAYPOINT", datetime.now().isoformat(timespec="seconds"), operation_id)
        items.append(item)
        self.waypoints_path.write_text(json.dumps([asdict(x) for x in items], indent=2), encoding="utf-8")
        return item

    def waypoints(self) -> list[Waypoint]:
        return self._load(self.waypoints_path, Waypoint)

    def upsert_mesh_node(self, node_id: str, latitude: float, longitude: float, label: str = "") -> MeshNode:
        items = {item.id: item for item in self.mesh_nodes()}
        item = MeshNode(node_id, float(latitude), float(longitude), label.strip() or node_id, datetime.now().isoformat(timespec="seconds"))
        items[item.id] = item
        self.mesh_path.write_text(json.dumps([asdict(x) for x in items.values()], indent=2), encoding="utf-8")
        return item

    def mesh_nodes(self) -> list[MeshNode]:
        return self._load(self.mesh_path, MeshNode)

    @staticmethod
    def _load(path: Path, cls):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return [cls(**item) for item in payload if isinstance(item, dict)]
        except (OSError, ValueError, TypeError):
            return []
