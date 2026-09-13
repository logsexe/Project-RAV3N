from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)


@dataclass(frozen=True)
class AppSpec:
    app_id: str
    label: str
    subtitle: str
    status: str


APP_SPECS = (
    AppSpec("radio", "RADIO", "Wideband receive / spectrum", "RX READY"),
    AppSpec("map", "MAP", "Offline navigation / position", "GPS"),
    AppSpec("mesh", "MESH", "Off-grid node communications", "MESH"),
    AppSpec("network", "NETWORK", "Local diagnostics / inventory", "READY"),
    AppSpec("intel", "INTEL", "Assets / evidence / timeline", "READY"),
    AppSpec("library", "LIBRARY", "Offline field knowledge", "READY"),
    AppSpec("files", "FILES", "Operation data / storage", "READY"),
    AppSpec("terminal", "TERMINAL", "Operator shell", "READY"),
    AppSpec("system", "SYSTEM", "Hardware / readiness", "READY"),
)


STYLE = """
QWidget {
    background: #050806;
    color: #d7f7df;
    font-family: 'DejaVu Sans Mono', 'Consolas', monospace;
    font-size: 13px;
}
QLabel#topbar, QLabel#bottombar {
    background: #09120c;
    color: #8cf5a7;
    padding: 6px 10px;
    font-weight: 700;
}
QLabel#title {
    color: #f0fff3;
    font-size: 22px;
    font-weight: 700;
}
QLabel#subtitle {
    color: #78a985;
    font-size: 12px;
}
QPushButton.appTile {
    background: #0b120d;
    border: 1px solid #284b31;
    border-radius: 8px;
    padding: 10px;
    text-align: left;
    color: #d7f7df;
    font-size: 15px;
    font-weight: 700;
}
QPushButton.appTile:focus, QPushButton.appTile:hover {
    background: #102116;
    border: 2px solid #63ff88;
    color: #ffffff;
}
QPushButton.navButton {
    background: #0b120d;
    border: 1px solid #284b31;
    border-radius: 6px;
    padding: 7px 14px;
}
QPushButton.navButton:focus, QPushButton.navButton:hover {
    border: 2px solid #63ff88;
}
QFrame#panel {
    background: #081009;
    border: 1px solid #284b31;
    border-radius: 8px;
}
QLabel#panelHeading {
    color: #8cf5a7;
    font-size: 16px;
    font-weight: 700;
}
QLabel#panelText {
    color: #b9d9c1;
    font-size: 13px;
}
"""


class FieldPage(QWidget):
    def __init__(self, title: str, subtitle: str, body: str, on_back: Callable[[], None]) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(10)

        heading = QHBoxLayout()
        back = QPushButton("< APPS")
        back.setProperty("class", "navButton")
        back.setObjectName("backButton")
        back.clicked.connect(on_back)
        heading.addWidget(back)
        heading.addStretch()
        root.addLayout(heading)

        title_label = QLabel(title)
        title_label.setObjectName("title")
        root.addWidget(title_label)
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("subtitle")
        root.addWidget(subtitle_label)

        panel = QFrame()
        panel.setObjectName("panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(18, 16, 18, 16)
        panel_heading = QLabel(f"{title} // RVN-01")
        panel_heading.setObjectName("panelHeading")
        panel_layout.addWidget(panel_heading)
        panel_text = QLabel(body)
        panel_text.setObjectName("panelText")
        panel_text.setWordWrap(True)
        panel_text.setAlignment(Qt.AlignmentFlag.AlignTop)
        panel_layout.addWidget(panel_text, 1)
        root.addWidget(panel, 1)


class Launcher(QWidget):
    def __init__(self, open_app: Callable[[str], None]) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(10)

        title = QLabel("APPLICATIONS")
        title.setObjectName("title")
        root.addWidget(title)
        subtitle = QLabel("Offline-first field computer // touch, keyboard and future rotary control")
        subtitle.setObjectName("subtitle")
        root.addWidget(subtitle)

        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)
        self.buttons: list[QPushButton] = []
        for index, spec in enumerate(APP_SPECS):
            button = QPushButton(f"{spec.label}\n{spec.subtitle}\n[{spec.status}]")
            button.setProperty("class", "appTile")
            button.setMinimumHeight(92)
            button.clicked.connect(lambda checked=False, app_id=spec.app_id: open_app(app_id))
            self.buttons.append(button)
            grid.addWidget(button, index // 3, index % 3)
        root.addLayout(grid, 1)
        if self.buttons:
            self.buttons[0].setFocus()


class FieldOSWindow(QMainWindow):
    """FIELD//OS V2 graphical shell for the RVN-01 800x480 display."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("RAVEN // FIELD//OS V2")
        self.resize(800, 480)
        self.setMinimumSize(800, 480)

        shell = QWidget()
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)

        self.topbar = QLabel()
        self.topbar.setObjectName("topbar")
        shell_layout.addWidget(self.topbar)

        self.stack = QStackedWidget()
        shell_layout.addWidget(self.stack, 1)

        self.bottombar = QLabel("RVN-01 // INSPECT -> SELECT -> STAGE -> REVIEW -> EXECUTE")
        self.bottombar.setObjectName("bottombar")
        shell_layout.addWidget(self.bottombar)
        self.setCentralWidget(shell)

        self.launcher = Launcher(self.open_app)
        self.stack.addWidget(self.launcher)
        self.pages: dict[str, QWidget] = {}
        self._build_pages()

        self.clock = QTimer(self)
        self.clock.timeout.connect(self.refresh_status)
        self.clock.start(1000)
        self.refresh_status()

    def _build_pages(self) -> None:
        content = {
            "radio": (
                "RADIO",
                "Receive-only RF workspace",
                "DEVICE      RTL-SDR / capability-gated\n"
                "MODE        RECEIVE ONLY\n"
                "FREQUENCY   ---.--- MHz\n"
                "DEMOD       --\n"
                "SIGNAL      --\n\n"
                "Spectrum, waterfall, presets, audio and recording attach here. "
                "FIELD//OS V2 does not provide a transmit path from this app.",
            ),
            "map": (
                "MAP",
                "Offline navigation and positioning",
                "GPS         waiting for provider\nPOSITION    --\nHEADING     --\nALTITUDE    --\n\n"
                "Offline tiles, tracks and waypoints will be stored locally on RVN-01.",
            ),
            "mesh": (
                "MESH",
                "Meshtastic nodes and messages",
                "LOCAL NODE  RVN-01\nLINK        waiting for hardware\nNODES       --\n\n"
                "Nodes, messages, positions and telemetry live here. Any transmission remains an explicit operator action.",
            ),
            "network": (
                "NETWORK",
                "Local visibility and authorised diagnostics",
                "LINK        capability service pending\n\n"
                "Local baseline, neighbours, device inventory and approved host inspection will be presented as workflows rather than raw tool menus.",
            ),
            "intel": (
                "INTEL",
                "Assets, evidence and operation timeline",
                "Structured operation data from the existing FIELD//OS backend will surface here in V2.",
            ),
            "library": (
                "LIBRARY",
                "Offline knowledge",
                "Manuals, reference material, Kiwix content and bundled FIELD//OS knowledge will be searchable here without Internet access.",
            ),
            "files": (
                "FILES",
                "Operation storage",
                "Operation files, recordings, captures and evidence staging will be exposed here with clear provenance and storage state.",
            ),
            "terminal": (
                "TERMINAL",
                "Operator shell",
                "The existing terminal/session backend will be embedded here after the graphical shell stabilises. V1.6 remains available as fieldos-tui during migration.",
            ),
            "system": (
                "SYSTEM",
                "RVN-01 hardware and readiness",
                "CPU         --\nTHERMAL     --\nNETWORK     --\nGPS         --\nMESH        --\nSTORAGE     --\nPOWER       --\n\n"
                "V2 will consume the non-blocking hardware state service rather than polling devices from the UI thread.",
            ),
        }
        for app_id, (title, subtitle, body) in content.items():
            page = FieldPage(title, subtitle, body, self.show_launcher)
            self.pages[app_id] = page
            self.stack.addWidget(page)

    def refresh_status(self) -> None:
        now = datetime.now().strftime("%H:%M:%S")
        self.topbar.setText(f"RAVEN // RVN-01     FIELD//OS V2.0     LINK --  GPS --  MESH --     {now}")

    def open_app(self, app_id: str) -> None:
        page = self.pages.get(app_id)
        if page is not None:
            self.stack.setCurrentWidget(page)
            back = page.findChild(QPushButton, "backButton")
            if back is not None:
                back.setFocus()

    def show_launcher(self) -> None:
        self.stack.setCurrentWidget(self.launcher)
        if self.launcher.buttons:
            self.launcher.buttons[0].setFocus()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape and self.stack.currentWidget() is not self.launcher:
            self.show_launcher()
            return
        super().keyPressEvent(event)


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(STYLE)
    window = FieldOSWindow()
    window.showFullScreen()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
