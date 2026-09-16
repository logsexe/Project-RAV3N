from __future__ import annotations

import math
import shutil
import sqlite3
import subprocess
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QRect
from PySide6.QtGui import QImage, QPainter

MAP_ROOTS = (
    Path.home() / "RAVEN" / "maps",
    Path.home() / "Maps",
    Path("/opt/raven/maps"),
    Path("/mnt/data/maps"),
)


@dataclass(frozen=True)
class MapPack:
    path: Path
    name: str
    min_zoom: int | None = None
    max_zoom: int | None = None


def discover_mbtiles() -> list[MapPack]:
    packs: list[MapPack] = []
    seen: set[Path] = set()
    for root in MAP_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*.mbtiles"):
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            name = path.stem
            min_zoom = max_zoom = None
            try:
                with sqlite3.connect(path) as db:
                    meta = dict(db.execute("select name, value from metadata").fetchall())
                    name = meta.get("name", name)
                    if meta.get("minzoom") is not None:
                        min_zoom = int(meta["minzoom"])
                    if meta.get("maxzoom") is not None:
                        max_zoom = int(meta["maxzoom"])
            except (sqlite3.Error, ValueError):
                pass
            packs.append(MapPack(resolved, name, min_zoom, max_zoom))
    return packs


def _mercator_tile(lat: float, lon: float, zoom: int) -> tuple[float, float]:
    lat = max(-85.05112878, min(85.05112878, lat))
    n = 2 ** zoom
    x = (lon + 180.0) / 360.0 * n
    lat_rad = math.radians(lat)
    y = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n
    return x, y


def render_mbtiles_image(path: Path, lat: float, lon: float, width: int, height: int, zoom: int = 14) -> QImage | None:
    """Render a centered MBTiles viewport into a worker-safe QImage."""
    if width <= 0 or height <= 0 or not path.is_file():
        return None
    center_x, center_y = _mercator_tile(lat, lon, zoom)
    tile_size = 256
    cols = width // tile_size + 3
    rows = height // tile_size + 3
    first_x = math.floor(center_x - cols / 2)
    first_y = math.floor(center_y - rows / 2)
    offset_x = int(width / 2 - (center_x - first_x) * tile_size)
    offset_y = int(height / 2 - (center_y - first_y) * tile_size)

    canvas = QImage(width, height, QImage.Format.Format_RGB32)
    canvas.fill(0x020503)
    painter = QPainter(canvas)
    any_tile = False
    try:
        with sqlite3.connect(path) as db:
            for row in range(rows):
                for col in range(cols):
                    x = first_x + col
                    y_xyz = first_y + row
                    if x < 0 or y_xyz < 0 or x >= 2 ** zoom or y_xyz >= 2 ** zoom:
                        continue
                    y_tms = (2 ** zoom - 1) - y_xyz
                    record = db.execute(
                        "select tile_data from tiles where zoom_level=? and tile_column=? and tile_row=?",
                        (zoom, x, y_tms),
                    ).fetchone()
                    if not record:
                        continue
                    image = QImage.fromData(record[0])
                    if image.isNull():
                        continue
                    any_tile = True
                    painter.drawImage(QRect(offset_x + col * tile_size, offset_y + row * tile_size, tile_size, tile_size), image)
    except sqlite3.Error:
        painter.end()
        return None
    painter.end()
    return canvas if any_tile else None


def rtl_fft(center_hz: int, sample_rate: int = 2_048_000, sample_count: int = 32768) -> list[float]:
    """Capture receive-only RTL-SDR IQ and return 256 normalized FFT bins."""
    rtl_sdr = shutil.which("rtl_sdr")
    if not rtl_sdr:
        return []
    try:
        import numpy as np
    except ImportError:
        return []
    try:
        proc = subprocess.run(
            [rtl_sdr, "-f", str(center_hz), "-s", str(sample_rate), "-n", str(sample_count), "-"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=4.0,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    raw = proc.stdout
    if len(raw) < 4096:
        return []
    iq = np.frombuffer(raw, dtype=np.uint8).astype(np.float32)
    if iq.size % 2:
        iq = iq[:-1]
    i = (iq[0::2] - 127.5) / 127.5
    q = (iq[1::2] - 127.5) / 127.5
    samples = i + 1j * q
    if samples.size < 1024:
        return []
    n = min(16384, samples.size)
    samples = samples[:n] * np.hanning(n)
    fft = np.fft.fftshift(np.fft.fft(samples))
    power = 20 * np.log10(np.abs(fft) + 1e-12)
    bins = 256
    chunk = max(1, len(power) // bins)
    reduced = [float(power[j:j + chunk].mean()) for j in range(0, chunk * bins, chunk)]
    peak = max(reduced) if reduced else 0.0
    return [value - peak - 28.0 for value in reduced]
