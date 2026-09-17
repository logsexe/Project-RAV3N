from __future__ import annotations

import os
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from .qt_app import FieldOSWindow as BaseFieldOSWindow, STYLE, _display_summary, load_bundled_fonts
from .visual_surfaces import MapCanvas, SpectrumCanvas


class FieldOSWindow(BaseFieldOSWindow):
    """FIELD//OS visual navigation and receive-only RF surfaces."""

    def __init__(self) -> None:
        super().__init__()
        self._replace_page("MAP", self._map_visual_page())
        self._replace_page("RADIO", self._radio_visual_page())
        self.preview_timer = QTimer(self)
        self.preview_timer.timeout.connect(self._preview_tick)
        # A lightweight watchdog replaces a permanent 5.5 Hz hidden animation.
        self.preview_timer.start(500)

    def _preview_tick(self) -> None:
        if self.stack.currentWidget() is self.pages.get("RADIO") and not self.spectrum_canvas.live:
            self.spectrum_canvas.advance_preview()

    def _replace_page(self, name: str, page: QWidget) -> None:
        old = self.pages[name]
        index = self.stack.indexOf(old)
        self.stack.removeWidget(old)
        old.deleteLater()
        self.stack.insertWidget(index, page)
        self.pages[name] = page

    def _map_visual_page(self) -> QWidget:
        page, layout = self._shell("MAP", "Offline navigation // live GNSS overlay")
        self.map_canvas = MapCanvas()
        layout.addWidget(self.map_canvas, 1)
        self.map_status = QLabel("GPS         PROBING")
        self.map_status.setObjectName("body")
        layout.addWidget(self.map_status)
        row = QHBoxLayout()
        refresh = QPushButton("REFRESH GPS"); refresh.clicked.connect(lambda: self.refresh_module("MAP")); row.addWidget(refresh)
        companion = QPushButton("OPEN QMAPSHACK"); companion.clicked.connect(lambda: self.launch_first_service("MAP")); row.addWidget(companion)
        layout.addLayout(row); self._back(layout)
        return page

    def _radio_visual_page(self) -> QWidget:
        page, layout = self._shell("RADIO", "Receive-only spectrum // waterfall")
        self.spectrum_canvas = SpectrumCanvas()
        layout.addWidget(self.spectrum_canvas, 1)
        self.radio_status = QLabel("RX DEVICE   PROBING")
        self.radio_status.setObjectName("body")
        layout.addWidget(self.radio_status)
        row = QHBoxLayout()
        self.frequency_input = QLineEdit("100.000")
        self.frequency_input.setPlaceholderText("MHz")
        row.addWidget(self.frequency_input)
        tune = QPushButton("TUNE"); tune.clicked.connect(self._tune_preview); row.addWidget(tune)
        refresh = QPushButton("REFRESH SDR"); refresh.clicked.connect(lambda: self.refresh_module("RADIO")); row.addWidget(refresh)
        companion = QPushButton("OPEN SDR TOOL"); companion.clicked.connect(lambda: self.launch_first_service("RADIO")); row.addWidget(companion)
        layout.addLayout(row); self._back(layout)
        return page

    def _tune_preview(self) -> None:
        try:
            mhz = float(self.frequency_input.text().strip())
        except ValueError:
            self.footer.setText("RVN-01 // RADIO // INVALID FREQUENCY")
            return
        if not 0.1 <= mhz <= 1800:
            self.footer.setText("RVN-01 // RADIO // FREQUENCY OUT OF PREVIEW RANGE")
            return
        self.spectrum_canvas.set_frequency(int(mhz * 1_000_000))
        self.footer.setText(f"RVN-01 // RADIO // {mhz:.3f} MHz // RX PREVIEW")

    def _collect_futures(self) -> None:
        map_future = self.futures.get("MAP")
        radio_future = self.futures.get("RADIO")
        map_value = None
        radio_value = None
        if map_future is not None and map_future.done():
            try: map_value = map_future.result()
            except Exception: pass
        if radio_future is not None and radio_future.done():
            try: radio_value = radio_future.result()
            except Exception: pass
        super()._collect_futures()
        if map_value is not None:
            self.map_canvas.set_fix(map_value.latitude, map_value.longitude, map_value.track, map_value.state)
        if radio_value is not None:
            self.spectrum_canvas.live = False
            if radio_value.rtl_sdr:
                self.footer.setText("RVN-01 // RADIO // RTL-SDR DETECTED // STREAM ADAPTER READY")

    def _tick(self) -> None:
        from datetime import datetime
        self.top.setText(f"RAVEN // RVN-01     FIELD//OS     {datetime.now().strftime('%H:%M:%S')}")


def main() -> int:
    print("FIELD//OS // visual surfaces", flush=True); print(_display_summary(), flush=True)
    if sys.platform.startswith("linux") and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        print("FIELD//OS: no graphical display is available in this shell.", file=sys.stderr, flush=True); return 2
    app = QApplication.instance() or QApplication(sys.argv); load_bundled_fonts(); app.setStyleSheet(STYLE)
    window = FieldOSWindow(); window.show() if "--windowed" in sys.argv else window.showFullScreen()
    print("FIELD//OS: Qt visual window created", flush=True); return app.exec()


if __name__ == "__main__": raise SystemExit(main())
