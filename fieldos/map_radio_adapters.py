from __future__ import annotations

import importlib.util
import math
import shutil
import sqlite3
import subprocess
import threading
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


def _fft_bins_from_iq(samples, bins: int = 256) -> list[float]:
    """Shared IQ -> normalized dB spectrum pipeline (Hanning window, FFT,
    fftshift, downsample to `bins`, normalize by subtracting the peak and a
    28.0 dB offset).

    Both `rtl_fft()` (one-shot subprocess capture) and `RtlSdrStream`
    (continuous pyrtlsdr capture) funnel their IQ samples through this one
    function, so a stream frame and a one-shot capture always produce bins
    in the same shape and normalization convention that
    `visual_surfaces.SpectrumCanvas.set_spectrum()` expects, regardless of
    which path produced them. `samples` must already be normalized complex
    IQ (real/imag roughly in [-1, 1]) as a numpy array.
    """
    import numpy as np

    if samples.size < 1024:
        return []
    n = min(16384, samples.size)
    windowed = samples[:n] * np.hanning(n)
    fft = np.fft.fftshift(np.fft.fft(windowed))
    power = 20 * np.log10(np.abs(fft) + 1e-12)
    chunk = max(1, len(power) // bins)
    reduced = [float(power[j:j + chunk].mean()) for j in range(0, chunk * bins, chunk)]
    peak = max(reduced) if reduced else 0.0
    return [value - peak - 28.0 for value in reduced]


def rtl_fft(center_hz: int, sample_rate: int = 2_048_000, sample_count: int = 32768) -> list[float]:
    """Capture receive-only RTL-SDR IQ and return 256 normalized FFT bins.

    One-shot subprocess capture via the `rtl_sdr` CLI: spawns a brand-new
    process, blocks until `sample_count` IQ samples arrive, exits. This is
    the universal fallback -- it only needs the `rtl_sdr` binary on PATH,
    not the `pyrtlsdr` Python bindings -- and stays exactly as it was before
    `RtlSdrStream` (below) existed, so nothing regresses for anyone without
    `pyrtlsdr` installed.
    """
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
    return _fft_bins_from_iq(samples)


class RtlSdrStream:
    """Continuous RTL-SDR spectrum source using `pyrtlsdr` (a ctypes wrapper
    around `librtlsdr`), replacing `rtl_fft()`'s process-per-snapshot capture
    with one open device handle that keeps streaming samples on a dedicated
    background thread.

    Architecture note -- why this isn't built on pyrtlsdr's own asyncio
    streaming mode:

    pyrtlsdr ships an asyncio-based `RtlSdr.stream()`/`.stop()` API (the
    `rtlsdraio` module; as of pyrtlsdr 0.5.0 it's folded directly into the
    default `RtlSdr` class exported from the package -- no separate extras
    or import needed to get it). It's designed for callers that already run
    an asyncio event loop and want `async for samples in sdr.stream(): ...`.

    FIELD//OS's Qt app doesn't run one. `_submit()` (qt_app.py) hands
    blocking callables to a plain `ThreadPoolExecutor`, and a 150ms
    `QTimer` (`_collect_futures`) polls `Future.done()` -- nothing here
    awaits a coroutine. Using `stream()` would mean spinning up a private
    asyncio event loop on a bare thread purely to redeliver each `stream()`
    item across a lock into a plain buffer this class would poll anyway,
    plus a cross-thread shutdown path (`asyncio.run_coroutine_threadsafe`
    calling the async `sdr.stop()` from a different thread's loop, racing
    whatever `stream()`'s internal `run_in_executor` task is doing at the
    time) that is exactly the kind of subtle concurrency bug this project
    has no RTL-SDR hardware on hand to shake out.

    Instead, this uses pyrtlsdr's plain synchronous `RtlSdr.read_samples()`
    in a `while` loop on one dedicated thread that owns the device for its
    entire lifetime. That achieves the actual goal stated for this feature
    -- continuous samples from one open device handle instead of a brand
    new `rtl_sdr` process every RADIO tick -- with a shutdown story that's
    just a `threading.Event` the loop checks every iteration (each
    `read_samples()` call is a few milliseconds at the sample counts used
    here), and no cross-thread coroutine machinery to get subtly wrong
    somewhere this can't be tested against real hardware.

    The Qt side never touches the device directly or owns this thread by
    reference beyond this object. `start()` (which blocks while the device
    opens) is submitted through the existing `_submit`/futures/timer
    machinery exactly once, like every other blocking adapter call in this
    codebase; after that, the cheap, always-fast `snapshot()` is submitted
    on the same cadence `rtl_fft()` used to be. `_collect_futures()` and
    `visual_surfaces.SpectrumCanvas.set_spectrum()` don't know or care which
    one produced the bins -- both go through `_fft_bins_from_iq()` above, so
    the shape and normalization convention are identical either way.
    """

    def __init__(self, sample_rate: int = 2_048_000, read_size: int = 16384, gain: str | float = "auto") -> None:
        self.sample_rate = sample_rate
        self.read_size = read_size
        self.gain = gain
        self._lock = threading.Lock()
        self._bins: list[float] = []
        self._center_hz: int | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, center_hz: int) -> bool:
        """Open the device and start the capture thread.

        Blocking (waits for the device to open or fail) -- always call this
        through `_submit`, never directly on the Qt thread. Never raises:
        any failure (pyrtlsdr not installed, numpy not installed, no
        librtlsdr shared library on the system, no device attached, a
        `librtlsdr` open error) returns False so the caller falls back to
        `rtl_fft()`.

        Note that `importlib.util.find_spec("rtlsdr")` only confirms the
        `pyrtlsdr` distribution is installed -- it does NOT confirm the
        device or even the underlying `librtlsdr` shared library are
        present. pyrtlsdr's own `rtlsdr/librtlsdr.py` loads `librtlsdr` at
        `import rtlsdr` time via `ctypes.CDLL`, and raises `ImportError`
        right there if no copy of the library can be found anywhere on the
        search path -- so `from rtlsdr import RtlSdr` itself, not just
        constructing `RtlSdr()`, can fail closed here. That import is
        deferred into `_run()` (the background thread) specifically so that
        failure -- along with every other failure mode below it -- is
        caught the same way.
        """
        if self.running:
            self.retune(center_hz)
            return True
        if importlib.util.find_spec("rtlsdr") is None or importlib.util.find_spec("numpy") is None:
            return False
        self._center_hz = center_hz
        self._stop.clear()
        ready = threading.Event()
        opened: list[bool] = []

        def _mark(success: bool) -> None:
            opened.append(success)
            ready.set()

        thread = threading.Thread(target=self._run, args=(_mark,), name="fieldos-rtlsdr-stream", daemon=True)
        try:
            thread.start()
        except Exception:
            return False
        self._thread = thread
        if not ready.wait(timeout=5.0) or not opened or not opened[0]:
            self.stop()
            return False
        return True

    def retune(self, center_hz: int) -> None:
        """Ask the capture thread to retune on its next loop iteration.

        `_center_hz` is a plain attribute, not lock-protected: CPython's GIL
        makes a single attribute read/write atomic, and the capture thread
        only ever reads the latest value (a torn read isn't possible for a
        single int reference) -- worst case it retunes one iteration later
        than requested, which is harmless here.
        """
        self._center_hz = center_hz

    def snapshot(self) -> list[float]:
        """Cheap, non-blocking read of the latest FFT bins.

        This is what the Qt timer submits in place of `rtl_fft()` once
        streaming is active -- it only takes a lock and copies a small
        list, no device I/O happens on the calling (executor) thread.
        """
        with self._lock:
            return list(self._bins)

    def stop(self, timeout: float = 2.0) -> None:
        """Signal the capture thread to exit and wait briefly for it.

        Safe to call multiple times, and safe to call when the stream was
        never successfully started.
        """
        self._stop.set()
        thread, self._thread = self._thread, None
        if thread is not None:
            thread.join(timeout=timeout)

    def _run(self, mark_opened) -> None:
        """Capture thread body: open the device once, then loop
        `read_samples()` -> FFT -> publish until `stop()` is called or the
        device raises. Always closes the device before returning, however
        it exits.
        """
        try:
            from rtlsdr import RtlSdr
        except Exception:
            mark_opened(False)
            return
        try:
            sdr = RtlSdr()
        except Exception:
            mark_opened(False)
            return
        try:
            sdr.sample_rate = self.sample_rate
            sdr.center_freq = self._center_hz
            sdr.gain = self.gain
        except Exception:
            mark_opened(False)
            try:
                sdr.close()
            except Exception:
                pass
            return
        mark_opened(True)
        try:
            while not self._stop.is_set():
                wanted = self._center_hz
                try:
                    samples = sdr.read_samples(self.read_size)
                except Exception:
                    break
                try:
                    bins = _fft_bins_from_iq(samples)
                except Exception:
                    bins = []
                if bins:
                    with self._lock:
                        self._bins = bins
                if self._center_hz != wanted:
                    try:
                        sdr.center_freq = self._center_hz
                    except Exception:
                        break
        finally:
            try:
                sdr.close()
            except Exception:
                pass
