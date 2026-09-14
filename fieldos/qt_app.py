from __future__ import annotations

import os
import platform
import socket
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

APPS = (
    ("RADIO", "Receive-only RF"),
    ("MAP", "Offline navigation"),
    ("MESH", "Meshtastic"),
    ("NETWORK", "Local diagnostics"),
    ("INTEL", "Operations / evidence"),
    ("LIBRARY", "Offline knowledge"),
    ("FILES", "Local storage"),
    ("TERMINAL", "Operator shell"),
    ("SYSTEM", "RVN-01 status"),
)

STYLE = """
QWidget { background:#050806; color:#d7f7df; font-family:'DejaVu Sans'; font-size:14px; }
QLabel#bar { background:#09120c; color:#8cf5a7; padding:7px 10px; font-weight:700; }
QLabel#hero { font-size:34px; font-weight:800; color:#ffffff; }
QLabel#title { font-size:24px; font-weight:700; color:#ffffff; }
QLabel#subtitle { color:#78a985; }
QLabel#body { color:#c6e2cc; }
QPushButton { background:#0b120d; border:1px solid #284b31; border-radius:8px; padding:12px; font-size:15px; font-weight:700; }
QPushButton:hover, QPushButton:focus { background:#102116; border:2px solid #63ff88; }
QPushButton#primary { background:#12341c; border:2px solid #63ff88; color:#ffffff; }
QPushButton#tile { min-height:88px; text-align:left; }
"""


class FieldOSWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("RAVEN // FIELD//OS V2")
        self.resize(800, 480)

        shell = QWidget()
        root = QVBoxLayout(shell)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.top = QLabel()
        self.top.setObjectName("bar")
        root.addWidget(self.top)

        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

        self.footer = QLabel("RVN-01 // FIELD//OS V2")
        self.footer.setObjectName("bar")
        root.addWidget(self.footer)
        self.setCentralWidget(shell)

        self.home = self._build_home()
        self.about = self._build_info_page(
            "ABOUT",
            "RAVEN // RVN-01",
            "FIELD//OS is the operator environment for the RVN-01 field computer.\n\n"
            "Designed as an offline-first portable system for navigation, communications, radio reception, local diagnostics, intelligence, storage and system control.\n\n"
            "V2 is being rebuilt around PySide6 with dedicated applications rather than a terminal-first interface.",
        )
        self.contact = self._build_info_page(
            "CONTACT",
            "PROJECT RAVEN",
            "Local build information and project references live inside the RAVEN repository.\n\n"
            "Repository: github.com/logsexe/Project-RAV3N\n"
            "Node: RVN-01\n"
            "Platform: FIELD//OS V2\n\n"
            "No external account or credential is required to enter FIELD//OS.",
        )
        self.launcher = self._build_launcher()

        for page in (self.home, self.about, self.contact, self.launcher):
            self.stack.addWidget(page)

        self.pages: dict[str, QWidget] = {}
        for name, subtitle in APPS:
            page = self._build_app_page(name, subtitle)
            self.pages[name] = page
            self.stack.addWidget(page)

        timer = QTimer(self)
        timer.timeout.connect(self._tick)
        timer.start(1000)
        self._tick()
        self.show_home()

    def _build_home(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(42, 34, 42, 34)
        layout.setSpacing(14)
        layout.addStretch()

        brand = QLabel("RAVEN")
        brand.setObjectName("hero")
        brand.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(brand)

        title = QLabel("FIELD//OS")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("RVN-01 // PORTABLE FIELD COMPUTER")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        begin = QPushButton("ENTER FIELD//OS")
        begin.setObjectName("primary")
        begin.clicked.connect(self.show_launcher)
        layout.addWidget(begin)

        nav = QHBoxLayout()
        about = QPushButton("ABOUT")
        about.clicked.connect(lambda: self.stack.setCurrentWidget(self.about))
        contact = QPushButton("CONTACT")
        contact.clicked.connect(lambda: self.stack.setCurrentWidget(self.contact))
        nav.addWidget(about)
        nav.addWidget(contact)
        layout.addLayout(nav)
        layout.addStretch()
        return page

    def _build_info_page(self, name: str, subtitle: str, text: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(12)
        title = QLabel(name)
        title.setObjectName("title")
        layout.addWidget(title)
        sub = QLabel(subtitle)
        sub.setObjectName("subtitle")
        layout.addWidget(sub)
        body = QLabel(text)
        body.setObjectName("body")
        body.setWordWrap(True)
        body.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(body, 1)
        back = QPushButton("< HOME")
        back.clicked.connect(self.show_home)
        layout.addWidget(back)
        return page

    def _build_launcher(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 14, 18, 14)
        title = QLabel("APPLICATIONS")
        title.setObjectName("title")
        layout.addWidget(title)
        subtitle = QLabel("Select a FIELD//OS module")
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)

        grid = QGridLayout()
        grid.setSpacing(10)
        self.buttons: list[QPushButton] = []
        for i, (name, desc) in enumerate(APPS):
            button = QPushButton(f"{name}\n{desc}")
            button.setObjectName("tile")
            button.clicked.connect(lambda checked=False, n=name: self.open_app(n))
            grid.addWidget(button, i // 3, i % 3)
            self.buttons.append(button)
        layout.addLayout(grid, 1)

        home = QPushButton("< HOME")
        home.clicked.connect(self.show_home)
        layout.addWidget(home)
        return page

    def _build_app_page(self, name: str, subtitle: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 18, 24, 18)
        layout.setSpacing(10)

        title = QLabel(name)
        title.setObjectName("title")
        layout.addWidget(title)
        sub = QLabel(subtitle)
        sub.setObjectName("subtitle")
        layout.addWidget(sub)

        body = QLabel(self._module_text(name))
        body.setObjectName("body")
        body.setAlignment(Qt.AlignmentFlag.AlignTop)
        body.setWordWrap(True)
        layout.addWidget(body, 1)

        back = QPushButton("< APPLICATIONS")
        back.clicked.connect(self.show_launcher)
        layout.addWidget(back)
        return page

    def _module_text(self, name: str) -> str:
        if name == "RADIO":
            return "STATUS      WAITING FOR SDR\nMODE        RECEIVE ONLY\nFREQUENCY   ---.--- MHz\n\nPlanned: tuner, spectrum, waterfall, presets, audio and recordings."
        if name == "MAP":
            return "GPS         WAITING FOR RECEIVER\nPOSITION    --\nHEADING     --\n\nPlanned: offline maps, tracks, waypoints and TAK overlays."
        if name == "MESH":
            return "LINK        WAITING FOR MESHTASTIC\nLOCAL NODE  RVN-01\nNODES       --\n\nPlanned: nodes, messages, positions and telemetry."
        if name == "NETWORK":
            host = socket.gethostname()
            return f"HOST        {host}\nMODE        LOCAL DIAGNOSTICS\n\nPlanned: interfaces, routes, neighbours, device inventory and operator-approved workflows."
        if name == "INTEL":
            return "Operations, assets, evidence and timeline will live here as structured local data."
        if name == "LIBRARY":
            return "Offline manuals, reference material, Kiwix content and RAVEN knowledge packs."
        if name == "FILES":
            return f"HOME        {Path.home()}\n\nPlanned: local file browser, recordings, captures and evidence staging."
        if name == "TERMINAL":
            return "Embedded operator terminal planned for V2.\n\nShell execution will remain explicit and operator-controlled."
        if name == "SYSTEM":
            return (
                f"HOST        {socket.gethostname()}\n"
                f"OS          {platform.system()} {platform.release()}\n"
                f"MACHINE     {platform.machine()}\n"
                f"PYTHON      {platform.python_version()}\n\n"
                "Next: CPU, thermal, memory, storage, interfaces, GPS, mesh and power telemetry."
            )
        return "FIELD//OS module."

    def _tick(self) -> None:
        self.top.setText(f"RAVEN // RVN-01     FIELD//OS 2.1 DEV     {datetime.now().strftime('%H:%M:%S')}")

    def open_app(self, name: str) -> None:
        self.stack.setCurrentWidget(self.pages[name])
        self.footer.setText(f"RVN-01 // {name} // ESC = APPLICATIONS")

    def show_home(self) -> None:
        self.stack.setCurrentWidget(self.home)
        self.footer.setText("RVN-01 // FIELD//OS V2 // ENTER TO BEGIN")

    def show_launcher(self) -> None:
        self.stack.setCurrentWidget(self.launcher)
        self.footer.setText("RVN-01 // APPLICATIONS // ESC = HOME")
        if self.buttons:
            self.buttons[0].setFocus()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            current = self.stack.currentWidget()
            if current is self.launcher or current in {self.about, self.contact}:
                self.show_home()
            elif current is self.home:
                self.close()
            else:
                self.show_launcher()
            return
        super().keyPressEvent(event)


def _display_summary() -> str:
    return (
        f"DISPLAY={os.environ.get('DISPLAY', '')!r} "
        f"WAYLAND_DISPLAY={os.environ.get('WAYLAND_DISPLAY', '')!r} "
        f"XDG_SESSION_TYPE={os.environ.get('XDG_SESSION_TYPE', '')!r}"
    )


def main() -> int:
    print("FIELD//OS V2.1 DEV // PySide6 startup", flush=True)
    print(_display_summary(), flush=True)

    if sys.platform.startswith("linux") and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        print(
            "FIELD//OS: no graphical display is available in this shell. Run from the RVN-01 desktop session or attach the active display session.",
            file=sys.stderr,
            flush=True,
        )
        return 2

    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(STYLE)
    window = FieldOSWindow()
    window.show() if "--windowed" in sys.argv else window.showFullScreen()
    print("FIELD//OS: Qt window created", flush=True)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
