from __future__ import annotations

import os
import sys
from datetime import datetime

from PySide6.QtWidgets import QApplication, QGridLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from .qt_map_radio_app import FieldOSWindow as V27FieldOSWindow
from .qt_app import STYLE, _display_summary


FIELD_APPS = (
    ("RADIO", "RX / SPECTRUM"),
    ("NAVIGATION", "MAP / GPS / WAYPOINTS"),
    ("MESH", "NODES / MESSAGES"),
    ("NETWORK", "LOCAL / DEVICES"),
    ("OPS", "MISSION / EVIDENCE"),
    ("LIBRARY", "OFFLINE KNOWLEDGE"),
    ("FILES", "LOCAL STORAGE"),
    ("TERMINAL", "OPERATOR SHELL"),
    ("RVN-01", "SYSTEM / HARDWARE"),
)


class FieldOSWindow(V27FieldOSWindow):
    """FIELD//OS V2.8 — task-oriented RVN-01 field-computer interface."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("RAVEN // FIELD//OS V2.8")

        # Preserve the proven V2.7 implementations while presenting them as
        # field tasks rather than implementation/service names.
        self.pages["NAVIGATION"] = self.pages["MAP"]
        self.pages["OPS"] = self.pages["INTEL"]
        self.pages["RVN-01"] = self.pages["SYSTEM"]

        # TAK is a geospatial capability, not a primary application. Keep its
        # page available internally for future NAVIGATION integration.
        self.tak_page = self.pages.get("TAK")

        old_launcher = self.launcher
        index = self.stack.indexOf(old_launcher)
        self.stack.removeWidget(old_launcher)
        old_launcher.deleteLater()
        self.launcher = self._field_launcher()
        self.stack.insertWidget(index, self.launcher)

        # Rename existing page headings to the operator-facing hierarchy.
        self._rename_page("NAVIGATION", "NAVIGATION", "Offline map // GPS // waypoints // tracks // TAK")
        self._rename_page("OPS", "OPS", "Active operation // notes // assets // evidence // timeline")
        self._rename_page("RVN-01", "RVN-01", "System // hardware // storage // power // services")

    def _field_launcher(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(6)

        title = QLabel("RAVEN // RVN-01")
        title.setObjectName("title")
        layout.addWidget(title)
        subtitle = QLabel("FIELD COMPUTER // SELECT APPLICATION")
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)

        grid = QGridLayout()
        grid.setSpacing(7)
        self.buttons = []
        for i, (name, desc) in enumerate(FIELD_APPS):
            button = QPushButton(f"{name}\n{desc}")
            button.setObjectName("tile")
            button.setMinimumHeight(82)
            button.clicked.connect(lambda checked=False, n=name: self.open_app(n))
            grid.addWidget(button, i // 3, i % 3)
            self.buttons.append(button)
        layout.addLayout(grid, 1)
        return page

    def _rename_page(self, name: str, title: str, subtitle: str) -> None:
        page = self.pages[name]
        labels = page.findChildren(QLabel)
        if labels:
            labels[0].setText(title)
        if len(labels) > 1:
            labels[1].setText(subtitle)

    def show_home(self) -> None:
        # V2.8 is an appliance: launcher is home. No web-style ENTER/ABOUT gate.
        if hasattr(self, "launcher"):
            self.show_launcher()
        else:
            super().show_home()

    def open_app(self, name: str) -> None:
        target = {"NAVIGATION": "NAVIGATION", "OPS": "OPS", "RVN-01": "RVN-01"}.get(name, name)
        page = self.pages.get(target)
        if page is None:
            self.footer.setText(f"RVN-01 // {name} // MODULE NOT PRESENT")
            return
        self.stack.setCurrentWidget(page)
        self.footer.setText(f"RVN-01 // {name} // READY // ESC/BACK APPLICATIONS")
        if name == "NAVIGATION":
            self.refresh_module("MAP")
        elif name in {"RADIO", "MESH", "LIBRARY"}:
            self.refresh_module(name)
        elif name in {"NETWORK", "RVN-01"}:
            self.refresh_local_state()

    def _tick(self) -> None:
        self.top.setText(f"RAVEN // RVN-01     FIELD//OS 2.8     {datetime.now().strftime('%H:%M:%S')}")


def main() -> int:
    print("FIELD//OS V2.8 // RVN-01 field launcher", flush=True)
    print(_display_summary(), flush=True)
    if sys.platform.startswith("linux") and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        print("FIELD//OS: no graphical display is available in this shell.", file=sys.stderr, flush=True)
        return 2
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(STYLE)
    window = FieldOSWindow()
    window.show() if "--windowed" in sys.argv else window.showFullScreen()
    print("FIELD//OS: V2.8 field-computer window created", flush=True)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
