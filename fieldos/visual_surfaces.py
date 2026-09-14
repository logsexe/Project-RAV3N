from __future__ import annotations

import math
import random
from collections import deque

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QWidget

GREEN = QColor("#63ff88")
MUTED = QColor("#315a3b")
GRID = QColor("#17301d")
TEXT = QColor("#bcebc7")
BG = QColor("#020503")


class MapCanvas(QWidget):
    """FIELD//OS navigation canvas with optional offline raster background."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(230)
        self.latitude: float | None = None
        self.longitude: float | None = None
        self.track: float | None = None
        self.fix_state = "WAITING FOR GPS"
        self.trail: deque[tuple[float, float]] = deque(maxlen=80)
        self.map_background: QPixmap | None = None
        self.map_label = "GRID"

    def set_fix(self, latitude: float | None, longitude: float | None, track: float | None, state: str) -> None:
        self.latitude, self.longitude, self.track, self.fix_state = latitude, longitude, track, state
        if latitude is not None and longitude is not None:
            point = (latitude, longitude)
            if not self.trail or self.trail[-1] != point:
                self.trail.append(point)
        self.update()

    def set_background(self, pixmap: QPixmap | None, label: str = "GRID") -> None:
        self.map_background = pixmap
        self.map_label = label
        self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), BG)
        w, h = self.width(), self.height()
        if self.map_background is not None and not self.map_background.isNull():
            p.drawPixmap(self.rect(), self.map_background)
            p.fillRect(self.rect(), QColor(0, 10, 2, 70))
        else:
            p.setPen(QPen(GRID, 1))
            for x in range(0, w, 40): p.drawLine(x, 0, x, h)
            for y in range(0, h, 40): p.drawLine(0, y, w, y)
        p.setPen(QPen(MUTED, 1, Qt.PenStyle.DashLine)); p.drawLine(w // 2, 0, w // 2, h); p.drawLine(0, h // 2, w, h // 2)

        p.setFont(QFont("DejaVu Sans Mono", 9)); p.setPen(TEXT)
        p.drawText(10, 18, f"RVN-NAV // {self.map_label}")
        p.drawText(10, h - 10, f"GNSS::{self.fix_state}")
        p.drawText(w - 155, 18, "N")
        p.setPen(QPen(GREEN, 2)); p.drawLine(w - 150, 36, w - 150, 12); p.drawLine(w - 150, 12, w - 155, 20); p.drawLine(w - 150, 12, w - 145, 20)

        if self.latitude is None or self.longitude is None:
            p.setPen(TEXT); p.setFont(QFont("DejaVu Sans", 13)); p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "NO POSITION FIX\nGPS trail will render here")
            return

        cx, cy = w / 2, h / 2
        if len(self.trail) > 1:
            lat0, lon0 = self.trail[-1]
            path = QPainterPath()
            for i, (lat, lon) in enumerate(self.trail):
                x = cx + (lon - lon0) * 70000
                y = cy - (lat - lat0) * 70000
                if i == 0: path.moveTo(x, y)
                else: path.lineTo(x, y)
            p.setPen(QPen(QColor("#2c8a43"), 2)); p.drawPath(path)

        p.setPen(QPen(GREEN, 2)); p.setBrush(QColor("#123d1d")); p.drawEllipse(QPointF(cx, cy), 8, 8)
        heading = math.radians(self.track or 0.0)
        p.drawLine(QPointF(cx, cy), QPointF(cx + math.sin(heading) * 25, cy - math.cos(heading) * 25))
        p.setPen(TEXT); p.drawText(10, 38, f"LAT {self.latitude:.6f}   LON {self.longitude:.6f}   HDG {(self.track or 0):.0f}°")


class SpectrumCanvas(QWidget):
    """Native receive-only spectrum/waterfall surface for FIELD//OS."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(250)
        self.center_hz = 100_000_000
        self.span_hz = 2_000_000
        self.live = False
        self.samples: list[float] = []
        self.waterfall: deque[list[float]] = deque(maxlen=54)
        self._phase = 0.0

    def set_frequency(self, center_hz: int) -> None:
        self.center_hz = center_hz; self.update()

    def set_spectrum(self, samples: list[float], live: bool = True) -> None:
        if samples:
            self.samples = samples[:256]
            self.waterfall.append(self.samples.copy())
        self.live = live
        self.update()

    def advance_preview(self) -> None:
        if self.live: return
        self._phase += 0.17
        values = []
        for i in range(128):
            noise = random.uniform(-3, 3)
            peak1 = 30 * math.exp(-((i - 38 - math.sin(self._phase) * 2) / 4) ** 2)
            peak2 = 20 * math.exp(-((i - 88) / 7) ** 2)
            values.append(-78 + noise + peak1 + peak2)
        self.samples = values; self.waterfall.append(values.copy()); self.update()

    def paintEvent(self, _event) -> None:
        p = QPainter(self); p.setRenderHint(QPainter.RenderHint.Antialiasing); p.fillRect(self.rect(), BG)
        w, h = self.width(), self.height(); spectrum_h = int(h * .52); wf_top = spectrum_h + 2
        p.setPen(QPen(GRID, 1))
        for x in range(0, w, 64): p.drawLine(x, 0, x, spectrum_h)
        for y in range(0, spectrum_h, 32): p.drawLine(0, y, w, y)
        p.setFont(QFont("DejaVu Sans Mono", 8)); p.setPen(TEXT)
        mhz = self.center_hz / 1e6; span = self.span_hz / 1e6
        p.drawText(8, 16, f"{mhz:.3f} MHz   SPAN {span:.1f} MHz   {'LIVE RX' if self.live else 'SIM PREVIEW'}")

        if self.samples:
            path = QPainterPath()
            n = max(1, len(self.samples) - 1)
            for i, value in enumerate(self.samples):
                x = i / n * w; norm = max(0.0, min(1.0, (value + 100) / 70)); y = spectrum_h - 8 - norm * (spectrum_h - 30)
                if i == 0: path.moveTo(x, y)
                else: path.lineTo(x, y)
            p.setPen(QPen(GREEN, 2)); p.drawPath(path)

        rows = list(self.waterfall)
        if rows:
            row_h = max(1, (h - wf_top) / len(rows))
            for r, values in enumerate(reversed(rows)):
                n = max(1, len(values))
                cell_w = w / n
                for i, value in enumerate(values):
                    level = max(0, min(255, int((value + 100) / 60 * 255)))
                    color = QColor(0, level, min(120, level // 2 + 20))
                    p.fillRect(QRectF(i * cell_w, wf_top + r * row_h, cell_w + .5, row_h + .5), color)
        p.setPen(QPen(MUTED, 1)); p.drawLine(0, wf_top, w, wf_top)
