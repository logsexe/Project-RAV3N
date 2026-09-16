from __future__ import annotations

import os
import sys
from concurrent.futures import Future

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QGridLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from .qt_app import _display_summary
from .qt_v3_app import FieldOSWindow as LibraryFieldOSWindow, V3_STYLE
from .rvn_status import RVNStatus, collect_rvn_status


HEALTH_STYLE = V3_STYLE + """
QLabel#rvnPanel {
    background:#07100a;
    color:#d7f7df;
    border:1px solid #284b31;
    border-radius:8px;
    padding:8px;
    font-family:'DejaVu Sans Mono';
    font-size:11px;
}
"""


class FieldOSWindow(LibraryFieldOSWindow):
    """FIELD//OS V3 with the RVN-01 hardware/system health dashboard."""

    def __init__(self) -> None:
        super().__init__()
        self.rvn_future: Future | None = None
        self.rvn_panels: dict[str, QLabel] = {}
        self._replace_page("RVN-01", self._rvn_page())

        self.rvn_timer = QTimer(self)
        self.rvn_timer.timeout.connect(self._collect_rvn_work)
        self.rvn_timer.start(250)

    def _rvn_page(self) -> QWidget:
        page, layout = self._shell("RVN-01", "System // power // hardware // USB // network // services")
        grid = QGridLayout()
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(6)

        for i, name in enumerate(("SYSTEM", "POWER", "HARDWARE", "USB", "NETWORK", "SERVICES")):
            panel = QLabel(f"{name}\n\nPROBING...")
            panel.setObjectName("rvnPanel")
            panel.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
            panel.setMinimumHeight(105)
            panel.setWordWrap(True)
            grid.addWidget(panel, i // 3, i % 3)
            self.rvn_panels[name] = panel

        layout.addLayout(grid, 1)
        refresh = QPushButton("REFRESH HEALTH")
        refresh.clicked.connect(self._refresh_rvn_status)
        layout.addWidget(refresh)
        self._back(layout)
        return page

    @staticmethod
    def _panel_text(title: str, values: tuple[tuple[str, str], ...]) -> str:
        rows = [title, ""]
        rows.extend(f"{key:<11} {value}" for key, value in values)
        return "\n".join(rows)

    def _refresh_rvn_status(self) -> None:
        if self.rvn_future is not None and not self.rvn_future.done():
            return
        for name, panel in self.rvn_panels.items():
            panel.setText(f"{name}\n\nPROBING...")
        self.footer.setText("RVN-01 // HEALTH // PROBING HARDWARE")
        self.rvn_future = self.executor.submit(collect_rvn_status)

    def _collect_rvn_work(self) -> None:
        if self.rvn_future is None or not self.rvn_future.done():
            return
        try:
            status: RVNStatus = self.rvn_future.result()
        except Exception as exc:
            self.rvn_panels["SYSTEM"].setText(f"SYSTEM\n\nHEALTH ERROR\n{type(exc).__name__}")
            self.footer.setText("RVN-01 // HEALTH // ERROR")
        else:
            values = {
                "SYSTEM": status.system,
                "POWER": status.power,
                "HARDWARE": status.hardware,
                "USB": status.usb,
                "NETWORK": status.network,
                "SERVICES": status.services,
            }
            for name, rows in values.items():
                self.rvn_panels[name].setText(self._panel_text(name, rows))
            self.footer.setText("RVN-01 // HEALTH // READY")
        self.rvn_future = None

    def open_app(self, name: str) -> None:
        if name == "RVN-01":
            self.stack.setCurrentWidget(self.pages["RVN-01"])
            self._refresh_rvn_status()
            return
        super().open_app(name)


def main() -> int:
    print("FIELD//OS V3 // library + RVN-01 health", flush=True)
    print(_display_summary(), flush=True)
    if sys.platform.startswith("linux") and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        print("FIELD//OS: no graphical display is available in this shell.", file=sys.stderr, flush=True)
        return 2
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(HEALTH_STYLE)
    window = FieldOSWindow()
    window.show() if "--windowed" in sys.argv else window.showFullScreen()
    print("FIELD//OS: V3 health dashboard window created", flush=True)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
