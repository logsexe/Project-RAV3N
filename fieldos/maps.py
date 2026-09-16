from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import json
import math
from pathlib import Path
import sqlite3

from fieldos.operations import _data_root


def bearing_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> tuple[float, float]:
    """Great-circle distance in metres and initial bearing in degrees, point 1 to point 2."""
    radius_m = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    distance = 2 * radius_m * math.asin(min(1.0, math.sqrt(a)))
    x = math.sin(dlambda) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlambda)
    bearing = (math.degrees(math.atan2(x, y)) + 360) % 360
    return distance, bearing


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
