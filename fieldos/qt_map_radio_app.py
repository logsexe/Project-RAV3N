from __future__ import annotations

import os
import sys

from PySide6.QtCore import QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication

from .map_radio_adapters import discover_mbtiles, render_mbtiles_image, rtl_fft
from .qt_visual_app import FieldOSWindow as VisualFieldOSWindow
from .qt_app import STYLE, _display_summary, load_bundled_fonts


class FieldOSWindow(VisualFieldOSWindow):
    """FIELD//OS V2.9 with demand-driven offline-map and RTL-SDR adapters."""

    RADIO_ACTIVE_MS = 1300
    RADIO_IDLE_MS = 12000
    MAP_PACK_ACTIVE_MS = 15000
    MAP_PACK_IDLE_MS = 60000

    def __init__(self) -> None:
        super().__init__()
        packs = discover_mbtiles()
        self.map_pack = packs[0] if packs else None
        self.map_zoom = 14
        self.last_map_center: tuple[float, float] | None = None

        self.radio_timer = QTimer(self)
        self.radio_timer.timeout.connect(self._radio_tick)
        self.radio_timer.start(self.RADIO_IDLE_MS)

        self.map_pack_timer = QTimer(self)
        self.map_pack_timer.timeout.connect(self._map_pack_tick)
        self.map_pack_timer.start(self.MAP_PACK_IDLE_MS)

        # One initial discovery pass is enough. Subsequent work is demand-driven
        # by the visible application or explicit operator refresh/tune actions.
        self.refresh_map_pack()

    def _current_page_is(self, name: str) -> bool:
        page = self.pages.get(name)
        return page is not None and self.stack.currentWidget() is page

    def _radio_tick(self) -> None:
        active = self._current_page_is("RADIO")
        wanted = self.RADIO_ACTIVE_MS if active else self.RADIO_IDLE_MS
        if self.radio_timer.interval() != wanted:
            self.radio_timer.setInterval(wanted)
        if active:
            self.refresh_live_radio()

    def _map_pack_tick(self) -> None:
        active = self._current_page_is("MAP") or self._current_page_is("NAVIGATION")
        wanted = self.MAP_PACK_ACTIVE_MS if active else self.MAP_PACK_IDLE_MS
        if self.map_pack_timer.interval() != wanted:
            self.map_pack_timer.setInterval(wanted)
        if active:
            self.refresh_map_pack()

    def refresh_map_pack(self) -> None:
        packs = discover_mbtiles()
        self.map_pack = packs[0] if packs else None
        if self.map_pack is None:
            if hasattr(self, "map_canvas"):
                self.map_canvas.set_background(None, "GRID // NO MBTILES")
            return
        if self.last_map_center is not None and "MAPTILES" not in self.futures:
            lat, lon = self.last_map_center
            self._submit(
                "MAPTILES",
                lambda: render_mbtiles_image(
                    self.map_pack.path,
                    lat,
                    lon,
                    max(320, self.map_canvas.width()),
                    max(180, self.map_canvas.height()),
                    self._effective_zoom(),
                ),
            )

    def _effective_zoom(self) -> int:
        if self.map_pack is None:
            return self.map_zoom
        zoom = self.map_zoom
        if self.map_pack.min_zoom is not None:
            zoom = max(zoom, self.map_pack.min_zoom)
        if self.map_pack.max_zoom is not None:
            zoom = min(zoom, self.map_pack.max_zoom)
        return zoom

    def refresh_live_radio(self) -> None:
        if not hasattr(self, "spectrum_canvas") or "RTLFFT" in self.futures:
            return
        center = self.spectrum_canvas.center_hz
        self._submit("RTLFFT", lambda: rtl_fft(center))

    def _collect_futures(self) -> None:
        map_future = self.futures.get("MAP")
        map_value = None
        if map_future is not None and map_future.done():
            try:
                map_value = map_future.result()
            except Exception:
                pass
        super()._collect_futures()

        if map_value is not None and map_value.latitude is not None and map_value.longitude is not None:
            center = (map_value.latitude, map_value.longitude)
            moved = self.last_map_center is None or abs(center[0] - self.last_map_center[0]) > 0.00008 or abs(center[1] - self.last_map_center[1]) > 0.00008
            self.last_map_center = center
            if moved and self.map_pack is not None and "MAPTILES" not in self.futures:
                self._submit(
                    "MAPTILES",
                    lambda: render_mbtiles_image(
                        self.map_pack.path,
                        center[0],
                        center[1],
                        max(320, self.map_canvas.width()),
                        max(180, self.map_canvas.height()),
                        self._effective_zoom(),
                    ),
                )

        tile_future = self.futures.get("MAPTILES")
        if tile_future is not None and tile_future.done():
            try:
                image = tile_future.result()
            except Exception:
                image = None
            if image is not None:
                label = f"MBTILES // {self.map_pack.name} // Z{self._effective_zoom()}" if self.map_pack else "MBTILES"
                self.map_canvas.set_background(QPixmap.fromImage(image), label)
                self.footer.setText(f"RVN-01 // MAP // OFFLINE PACK {self.map_pack.name if self.map_pack else 'READY'}")
            elif self.map_pack is not None:
                self.map_canvas.set_background(None, f"MBTILES // NO TILE @ Z{self._effective_zoom()}")
            del self.futures["MAPTILES"]

        fft_future = self.futures.get("RTLFFT")
        if fft_future is not None and fft_future.done():
            try:
                bins = fft_future.result()
            except Exception:
                bins = []
            if bins:
                self.spectrum_canvas.set_spectrum(bins, live=True)
                self.radio_status.setText("RX DEVICE   RTL-SDR LIVE\nFFT         256 BINS\nMODE        RECEIVE ONLY")
                self.footer.setText(f"RVN-01 // RADIO // LIVE RX // {self.spectrum_canvas.center_hz / 1e6:.3f} MHz")
            else:
                self.spectrum_canvas.live = False
            del self.futures["RTLFFT"]

    def _tune_preview(self) -> None:
        super()._tune_preview()
        self.spectrum_canvas.live = False
        self.refresh_live_radio()

    def _tick(self) -> None:
        from datetime import datetime
        self.top.setText(f"RAVEN // RVN-01     FIELD//OS 2.9     {datetime.now().strftime('%H:%M:%S')}")


def main() -> int:
    print("FIELD//OS V2.9 // efficiency pass", flush=True)
    print(_display_summary(), flush=True)
    if sys.platform.startswith("linux") and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        print("FIELD//OS: no graphical display is available in this shell.", file=sys.stderr, flush=True)
        return 2
    app = QApplication.instance() or QApplication(sys.argv)
    load_bundled_fonts()
    app.setStyleSheet(STYLE)
    window = FieldOSWindow()
    window.show() if "--windowed" in sys.argv else window.showFullScreen()
    print("FIELD//OS: V2.9 graphical window created", flush=True)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
