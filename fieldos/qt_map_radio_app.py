from __future__ import annotations

import os
import sys

from PySide6.QtCore import QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication

from .map_radio_adapters import RtlSdrStream, discover_mbtiles, render_mbtiles_image, rtl_fft
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

        # `rtl_stream`, once opened, owns a dedicated background thread and
        # an open RTL-SDR device handle (see RtlSdrStream in
        # map_radio_adapters.py) -- it is not a QTimer and never runs on
        # self.executor, so closeEvent() below has to stop it explicitly.
        # Nothing during any ancestor's __init__ calls refresh_live_radio()
        # or _radio_tick() (both are only reachable via radio_timer, started
        # further down in this same method, or explicit operator actions
        # like open_app("RADIO")/_tune_preview()), so it's safe to set this
        # up here rather than before super().__init__().
        self.rtl_stream: RtlSdrStream | None = None
        self._rtl_stream_start_attempted = False

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
        if not hasattr(self, "spectrum_canvas"):
            return
        center = self.spectrum_canvas.center_hz

        # Prefer the continuous pyrtlsdr stream once it's up: retune it in
        # place and just poll its latest bins (cheap -- a lock + list copy,
        # no device I/O on this thread), instead of spawning a fresh
        # rtl_sdr process this tick.
        if self.rtl_stream is not None and self.rtl_stream.running:
            self.rtl_stream.retune(center)
            if "RTLFFT" not in self.futures:
                self._submit("RTLFFT", self.rtl_stream.snapshot)
            return

        # Try to open the stream exactly once per window lifetime. This is
        # deliberately not retried on a timer: with no confirmed RTL-SDR
        # hardware to validate reconnect behavior against, a single
        # permanent fallback to the one-shot subprocess path is the safer
        # choice over polling a possibly-absent device every tick forever.
        # A hot-plugged device won't be picked up without restarting
        # FIELD//OS -- see the PR description for why this is an accepted
        # trade-off for now.
        if not self._rtl_stream_start_attempted and "RTLSTREAM" not in self.futures:
            if self.rtl_stream is None:
                self.rtl_stream = RtlSdrStream()
            self._submit("RTLSTREAM", lambda stream=self.rtl_stream, c=center: stream.start(c))
            return

        if "RTLFFT" not in self.futures:
            self._submit("RTLFFT", lambda: rtl_fft(center))

    def _collect_futures(self) -> None:
        map_future = self.futures.get("MAP")
        map_value = None
        if map_future is not None and map_future.done():
            try:
                map_value = map_future.result()
            except Exception:
                pass

        # MAPTILES/RTLSTREAM/RTLFFT are keys qt_app.py's base
        # _collect_futures() (called via super() a few lines down) doesn't
        # recognize. That base method's per-key loop unconditionally does
        # `del self.futures[key]` for *any* done future once it's inspected
        # it, matched or not -- so reading self.futures.get(...) for these
        # three *after* calling super() would already find them gone this
        # same tick (this was a real, pre-existing bug: MAPTILES/RTLFFT
        # results were being silently discarded here before this method's
        # own code ever saw them, since super()'s generic loop always wins
        # the race for a key it doesn't otherwise handle -- confirmed with a
        # round trip through the real futures/timer machinery while adding
        # RTLSTREAM below, not just by inspection). Peek and capture their
        # results now, before super() runs, matching the MAP/RADIO pattern
        # qt_visual_app.py already uses one tier up and the
        # MESHNODES/MESHCONNECT pattern qt_field_app.py uses one tier down.
        tile_future = self.futures.get("MAPTILES")
        tile_done = tile_future is not None and tile_future.done()
        tile_image = None
        if tile_done:
            try:
                tile_image = tile_future.result()
            except Exception:
                tile_image = None

        stream_future = self.futures.get("RTLSTREAM")
        stream_done = stream_future is not None and stream_future.done()
        stream_started = False
        if stream_done:
            try:
                stream_started = stream_future.result()
            except Exception:
                stream_started = False

        fft_future = self.futures.get("RTLFFT")
        fft_done = fft_future is not None and fft_future.done()
        fft_bins: list[float] = []
        if fft_done:
            try:
                fft_bins = fft_future.result()
            except Exception:
                fft_bins = []

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

        if tile_done:
            if tile_image is not None:
                label = f"MBTILES // {self.map_pack.name} // Z{self._effective_zoom()}" if self.map_pack else "MBTILES"
                self.map_canvas.set_background(QPixmap.fromImage(tile_image), label)
                self.footer.setText(f"RVN-01 // MAP // OFFLINE PACK {self.map_pack.name if self.map_pack else 'READY'}")
            elif self.map_pack is not None:
                self.map_canvas.set_background(None, f"MBTILES // NO TILE @ Z{self._effective_zoom()}")

        if stream_done:
            self._rtl_stream_start_attempted = True
            if not stream_started:
                # Nothing worth holding onto -- the attempt already failed
                # closed inside RtlSdrStream.start() (no pyrtlsdr, no
                # device, an open error, ...). Every future tick falls
                # straight through to the rtl_fft() one-shot path.
                self.rtl_stream = None

        if fft_done:
            if fft_bins:
                self.spectrum_canvas.set_spectrum(fft_bins, live=True)
                source = "STREAM" if (self.rtl_stream is not None and self.rtl_stream.running) else "SNAPSHOT"
                self.radio_status.setText(f"RX DEVICE   RTL-SDR LIVE\nFFT         256 BINS\nMODE        RECEIVE ONLY // {source}")
                self.footer.setText(f"RVN-01 // RADIO // LIVE RX // {self.spectrum_canvas.center_hz / 1e6:.3f} MHz")
            else:
                self.spectrum_canvas.live = False

    def closeEvent(self, event) -> None:
        # rtl_stream, once opened, owns a dedicated background thread and an
        # open RTL-SDR device handle -- it is not a QTimer (findChildren(QTimer)
        # in qt_app.py's closeEvent won't see it) and start()/snapshot() only
        # ever ran *on* self.executor, never *as* self.executor, so shutting
        # the executor down (also in qt_app.py's closeEvent) doesn't stop the
        # persistent thread either. Same precedent as qt_field_app.py's
        # mesh_interface.close() override: stop our own resource, then let
        # the chain's closeEvent do the rest.
        if self.rtl_stream is not None:
            try:
                self.rtl_stream.stop()
            except Exception:
                pass
        super().closeEvent(event)

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
