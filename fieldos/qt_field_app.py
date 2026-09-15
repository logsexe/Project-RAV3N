from __future__ import annotations

import os
import sys
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QGridLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from .qt_map_radio_app import FieldOSWindow as V27FieldOSWindow
from .qt_app import STYLE, _display_summary


FIELD_APPS = (
    ("RADIO", "◉", "RX / SPECTRUM"),
    ("NAVIGATION", "⌖", "MAP / GPS / WAYPOINTS"),
    ("MESH", "⌁", "NODES / MESSAGES"),
    ("NETWORK", "◎", "LOCAL / DEVICES"),
    ("OPS", "◇", "MISSION / EVIDENCE"),
    ("LIBRARY", "▤", "OFFLINE KNOWLEDGE"),
    ("FILES", "▱", "LOCAL STORAGE"),
    ("TERMINAL", ">_", "OPERATOR SHELL"),
    ("RVN-01", "◆", "SYSTEM / HARDWARE"),
)

V28_STYLE = STYLE + """
QWidget#fieldLauncher { background:#030604; }
QLabel#launcherBrand { color:#ffffff; font-size:20px; font-weight:800; letter-spacing:2px; }
QLabel#launcherMeta { color:#6f9d7a; font-size:11px; font-weight:700; }
QLabel#launcherHint { color:#496b52; font-size:10px; }
QPushButton#appCard {
    background:#08100b;
    color:#effff3;
    border:1px solid #1e4028;
    border-radius:12px;
    padding:8px 10px;
    text-align:left;
    font-size:14px;
    font-weight:800;
}
QPushButton#appCard:hover, QPushButton#appCard:focus {
    background:#0d1c12;
    border:2px solid #63ff88;
}
QPushButton#appCard:pressed { background:#14331d; }
"""


class FieldOSWindow(V27FieldOSWindow):
    """FIELD//OS V2.8 — graphical task-oriented RVN-01 field computer."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("RAVEN // FIELD//OS V2.8")

        # Keep the mature V2.7 graphical application surfaces. V2.8 changes
        # operator-facing hierarchy, not the GUI foundation.
        self.pages["NAVIGATION"] = self.pages["MAP"]
        self.pages["OPS"] = self.pages["INTEL"]
        self.pages["RVN-01"] = self.pages["SYSTEM"]
        self.tak_page = self.pages.get("TAK")

        old_launcher = self.launcher
        index = self.stack.indexOf(old_launcher)
        self.stack.removeWidget(old_launcher)
        old_launcher.deleteLater()
        self.launcher = self._field_launcher()
        self.stack.insertWidget(index, self.launcher)

        self._rename_page("NAVIGATION", "NAVIGATION", "Offline map // GPS // waypoints // tracks // TAK")
        self._rename_page("OPS", "OPS", "Active operation // notes // assets // evidence // timeline")
        self._rename_page("RVN-01", "RVN-01", "System // hardware // storage // power // services")

    def _field_launcher(self) -> QWidget:
        page = QWidget()
        page.setObjectName("fieldLauncher")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(5)

        header = QLabel("RAVEN // RVN-01")
        header.setObjectName("launcherBrand")
        layout.addWidget(header)

        meta = QLabel("FIELD//OS 2.8   •   OFFLINE FIELD COMPUTER   •   SELECT APPLICATION")
        meta.setObjectName("launcherMeta")
        layout.addWidget(meta)

        grid = QGridLayout()
        grid.setHorizontalSpacing(7)
        grid.setVerticalSpacing(7)
        grid.setContentsMargins(0, 3, 0, 2)
        self.buttons = []
        for i, (name, glyph, desc) in enumerate(FIELD_APPS):
            # One large graphical/touch target per application. The glyph is a
            # lightweight UI mark, not a dependency on an external icon pack.
            button = QPushButton(f"{glyph}   {name}\n      {desc}")
            button.setObjectName("appCard")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setMinimumHeight(88)
            button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            button.clicked.connect(lambda checked=False, n=name: self.open_app(n))
            grid.addWidget(button, i // 3, i % 3)
            self.buttons.append(button)
        layout.addLayout(grid, 1)

        hint = QLabel("TOUCH / ENTER OPEN   •   ESC APPLICATIONS   •   CTRL+Q EXIT")
        hint.setObjectName("launcherHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)
        return page

    def _rename_page(self, name: str, title: str, subtitle: str) -> None:
        page = self.pages[name]
        labels = page.findChildren(QLabel)
        if labels:
            labels[0].setText(title)
        if len(labels) > 1:
            labels[1].setText(subtitle)

    def show_home(self) -> None:
        # FIELD//OS behaves as an appliance. The graphical application dashboard
        # is home; the old website-like entry page remains out of the runtime flow.
        if hasattr(self, "launcher"):
            self.show_launcher()
        else:
            super().show_home()

    def open_app(self, name: str) -> None:
        page = self.pages.get(name)
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
        self.top.setText(
            f"RAVEN // RVN-01     FIELD//OS 2.8     "
            f"GPS •  MESH •  NET •  SDR •     {datetime.now().strftime('%H:%M:%S')}"
        )


def main() -> int:
    print("FIELD//OS V2.8 // graphical RVN-01 field computer", flush=True)
    print(_display_summary(), flush=True)
    if sys.platform.startswith("linux") and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        print("FIELD//OS: no graphical display is available in this shell.", file=sys.stderr, flush=True)
        return 2
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(V28_STYLE)
    window = FieldOSWindow()
    window.show() if "--windowed" in sys.argv else window.showFullScreen()
    print("FIELD//OS: V2.8 graphical field-computer window created", flush=True)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
