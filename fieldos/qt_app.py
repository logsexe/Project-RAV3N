from __future__ import annotations

import os
import sys
from datetime import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
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
QLabel#title { font-size:24px; font-weight:700; color:#ffffff; }
QLabel#subtitle { color:#78a985; }
QPushButton { background:#0b120d; border:1px solid #284b31; border-radius:8px; padding:12px; text-align:left; font-size:16px; font-weight:700; }
QPushButton:focus, QPushButton:hover { background:#102116; border:2px solid #63ff88; }
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

        footer = QLabel("RVN-01 // FIELD//OS V2 // ESC = APPS")
        footer.setObjectName("bar")
        root.addWidget(footer)
        self.setCentralWidget(shell)

        self.launcher = self._build_launcher()
        self.stack.addWidget(self.launcher)
        self.pages: dict[str, QWidget] = {}
        for name, subtitle in APPS:
            page = self._build_page(name, subtitle)
            self.pages[name] = page
            self.stack.addWidget(page)

        timer = QTimer(self)
        timer.timeout.connect(self._tick)
        timer.start(1000)
        self._tick()

    def _build_launcher(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(18, 14, 18, 14)
        title = QLabel("APPLICATIONS")
        title.setObjectName("title")
        layout.addWidget(title)
        subtitle = QLabel("RAVEN field computer // minimal PySide6 baseline")
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)

        grid = QGridLayout()
        grid.setSpacing(10)
        self.buttons: list[QPushButton] = []
        for i, (name, desc) in enumerate(APPS):
            button = QPushButton(f"{name}\n{desc}")
            button.setMinimumHeight(88)
            button.clicked.connect(lambda checked=False, n=name: self.open_app(n))
            grid.addWidget(button, i // 3, i % 3)
            self.buttons.append(button)
        layout.addLayout(grid, 1)
        if self.buttons:
            self.buttons[0].setFocus()
        return page

    def _build_page(self, name: str, subtitle: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(22, 18, 22, 18)
        title = QLabel(name)
        title.setObjectName("title")
        layout.addWidget(title)
        sub = QLabel(subtitle)
        sub.setObjectName("subtitle")
        layout.addWidget(sub)
        body = QLabel(
            f"{name} // RVN-01\n\n"
            "V2 baseline operational.\n"
            "Hardware and service integration will be added here incrementally."
        )
        body.setAlignment(Qt.AlignmentFlag.AlignTop)
        body.setWordWrap(True)
        layout.addWidget(body, 1)
        back = QPushButton("< APPS")
        back.clicked.connect(self.show_launcher)
        layout.addWidget(back)
        return page

    def _tick(self) -> None:
        self.top.setText(
            f"RAVEN // RVN-01     FIELD//OS 2.0.1     {datetime.now().strftime('%H:%M:%S')}"
        )

    def open_app(self, name: str) -> None:
        self.stack.setCurrentWidget(self.pages[name])

    def show_launcher(self) -> None:
        self.stack.setCurrentWidget(self.launcher)
        if self.buttons:
            self.buttons[0].setFocus()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
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
    print("FIELD//OS V2.0.1 // minimal PySide6 startup", flush=True)
    print(_display_summary(), flush=True)

    if sys.platform.startswith("linux") and not (
        os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
    ):
        print(
            "FIELD//OS: no graphical display is available in this shell. "
            "Run 'fieldos' from the RVN-01 desktop session, or attach this shell to the active display session.",
            file=sys.stderr,
            flush=True,
        )
        return 2

    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(STYLE)
    window = FieldOSWindow()

    if "--windowed" in sys.argv:
        window.show()
    else:
        window.showFullScreen()

    print("FIELD//OS: Qt window created", flush=True)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
