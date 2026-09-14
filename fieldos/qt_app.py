from __future__ import annotations

import os
import platform
import shutil
import socket
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QProcess, Qt, QTimer
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QTextEdit,
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
QLabel#section { color:#8cf5a7; font-size:15px; font-weight:700; }
QPushButton { background:#0b120d; border:1px solid #284b31; border-radius:8px; padding:10px; font-size:14px; font-weight:700; }
QPushButton:hover, QPushButton:focus { background:#102116; border:2px solid #63ff88; }
QPushButton#primary { background:#12341c; border:2px solid #63ff88; color:#ffffff; }
QPushButton#tile { min-height:88px; text-align:left; }
QLineEdit, QTextEdit { background:#020503; border:1px solid #284b31; color:#d7f7df; padding:8px; selection-background-color:#1f5d31; }
QLineEdit:focus, QTextEdit:focus { border:2px solid #63ff88; }
"""


def _read_cpu_temp() -> str:
    for candidate in (
        Path("/sys/class/thermal/thermal_zone0/temp"),
        Path("/sys/class/hwmon/hwmon0/temp1_input"),
    ):
        try:
            value = float(candidate.read_text().strip()) / 1000.0
            return f"{value:.1f} C"
        except (OSError, ValueError):
            continue
    return "--"


def _read_uptime() -> str:
    try:
        seconds = int(float(Path("/proc/uptime").read_text().split()[0]))
    except (OSError, ValueError, IndexError):
        return "--"
    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60
    return f"{hours}h {minutes}m"


def _read_memory() -> str:
    try:
        values: dict[str, int] = {}
        for line in Path("/proc/meminfo").read_text().splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            values[key] = int(value.strip().split()[0])
        total = values["MemTotal"] / 1024
        available = values["MemAvailable"] / 1024
        used = total - available
        return f"{used:.0f}/{total:.0f} MiB"
    except (OSError, ValueError, KeyError, IndexError):
        return "--"


def _storage_summary() -> str:
    try:
        usage = shutil.disk_usage(Path.home())
        used = usage.used / (1024 ** 3)
        total = usage.total / (1024 ** 3)
        return f"{used:.1f}/{total:.1f} GiB"
    except OSError:
        return "--"


def _primary_ip() -> str:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("192.0.2.1", 9))
        return sock.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "--"
    finally:
        sock.close()


class FieldOSWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("RAVEN // FIELD//OS V2")
        self.resize(800, 480)
        self.command_process: QProcess | None = None

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
            "V2 is built around PySide6 with dedicated applications and a small local service layer.",
        )
        self.contact = self._build_info_page(
            "CONTACT",
            "PROJECT RAVEN",
            "Project reference: github.com/logsexe/Project-RAV3N\n\n"
            "Node: RVN-01\nPlatform: FIELD//OS V2\n\n"
            "No account or credential is required to enter FIELD//OS.",
        )
        self.launcher = self._build_launcher()

        for page in (self.home, self.about, self.contact, self.launcher):
            self.stack.addWidget(page)

        self.pages: dict[str, QWidget] = {}
        self.pages["RADIO"] = self._build_radio_page()
        self.pages["MAP"] = self._build_map_page()
        self.pages["MESH"] = self._build_mesh_page()
        self.pages["NETWORK"] = self._build_network_page()
        self.pages["INTEL"] = self._build_intel_page()
        self.pages["LIBRARY"] = self._build_library_page()
        self.pages["FILES"] = self._build_files_page()
        self.pages["TERMINAL"] = self._build_terminal_page()
        self.pages["SYSTEM"] = self._build_system_page()
        for page in self.pages.values():
            self.stack.addWidget(page)

        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._tick)
        self.clock_timer.start(1000)
        self.system_timer = QTimer(self)
        self.system_timer.timeout.connect(self.refresh_local_state)
        self.system_timer.start(2000)
        self._tick()
        self.refresh_local_state()
        self.show_home()

    def _page_shell(self, name: str, subtitle: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 18, 24, 18)
        layout.setSpacing(8)
        title = QLabel(name)
        title.setObjectName("title")
        layout.addWidget(title)
        sub = QLabel(subtitle)
        sub.setObjectName("subtitle")
        layout.addWidget(sub)
        return page, layout

    def _add_back(self, layout: QVBoxLayout) -> None:
        back = QPushButton("< APPLICATIONS")
        back.clicked.connect(self.show_launcher)
        layout.addWidget(back)

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
        page, layout = self._page_shell(name, subtitle)
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
        page, layout = self._page_shell("APPLICATIONS", "Select a FIELD//OS module")
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

    def _build_radio_page(self) -> QWidget:
        page, layout = self._page_shell("RADIO", "Receive-only RF workspace")
        self.radio_status = QLabel(
            "DEVICE      WAITING FOR SDR\nMODE        RECEIVE ONLY\nFREQUENCY   ---.--- MHz\nDEMOD       --\nSIGNAL      --\n\n"
            "Tuner, spectrum, waterfall, presets, audio and recordings will activate when a supported SDR is connected."
        )
        self.radio_status.setObjectName("body")
        self.radio_status.setWordWrap(True)
        layout.addWidget(self.radio_status, 1)
        self._add_back(layout)
        return page

    def _build_map_page(self) -> QWidget:
        page, layout = self._page_shell("MAP", "Offline navigation and positioning")
        self.map_status = QLabel(
            "GPS         WAITING FOR RECEIVER\nPOSITION    --\nHEADING     --\nALTITUDE    --\n\n"
            "Offline tiles, tracks, waypoints and TAK overlays attach here."
        )
        self.map_status.setObjectName("body")
        self.map_status.setWordWrap(True)
        layout.addWidget(self.map_status, 1)
        self._add_back(layout)
        return page

    def _build_mesh_page(self) -> QWidget:
        page, layout = self._page_shell("MESH", "Meshtastic nodes and messages")
        self.mesh_status = QLabel(
            "LINK        WAITING FOR MESHTASTIC\nLOCAL NODE  RVN-01\nNODES       --\nMESSAGES    --\n\n"
            "Nodes, messages, positions and telemetry will appear here. Transmission remains an explicit operator action."
        )
        self.mesh_status.setObjectName("body")
        self.mesh_status.setWordWrap(True)
        layout.addWidget(self.mesh_status, 1)
        self._add_back(layout)
        return page

    def _build_network_page(self) -> QWidget:
        page, layout = self._page_shell("NETWORK", "Local diagnostics and inventory")
        self.network_status = QLabel()
        self.network_status.setObjectName("body")
        self.network_status.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.network_status, 1)
        refresh = QPushButton("REFRESH LOCAL STATE")
        refresh.clicked.connect(self.refresh_local_state)
        layout.addWidget(refresh)
        self._add_back(layout)
        return page

    def _build_intel_page(self) -> QWidget:
        page, layout = self._page_shell("INTEL", "Operations, evidence and timeline")
        body = QLabel(
            "ACTIVE OPERATION   LOCAL\nASSETS             0\nEVIDENCE           0\nEVENTS             0\n\n"
            "This surface is ready for the lightweight V2 operation store. No legacy database is loaded into the GUI runtime."
        )
        body.setObjectName("body")
        body.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(body, 1)
        self._add_back(layout)
        return page

    def _build_library_page(self) -> QWidget:
        page, layout = self._page_shell("LIBRARY", "Offline field knowledge")
        body = QLabel(
            "SOURCE      LOCAL ONLY\nINDEX       READY FOR CONTENT\n\n"
            "Planned collections: RAVEN manuals, radio reference, field procedures, offline encyclopaedia content and hardware documentation."
        )
        body.setObjectName("body")
        body.setWordWrap(True)
        layout.addWidget(body, 1)
        self._add_back(layout)
        return page

    def _build_files_page(self) -> QWidget:
        page, layout = self._page_shell("FILES", "Local operation storage")
        self.files_status = QLabel()
        self.files_status.setObjectName("body")
        self.files_status.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.files_status, 1)
        refresh = QPushButton("REFRESH DIRECTORY")
        refresh.clicked.connect(self.refresh_local_state)
        layout.addWidget(refresh)
        self._add_back(layout)
        return page

    def _build_terminal_page(self) -> QWidget:
        page, layout = self._page_shell("TERMINAL", "Operator-controlled local shell")
        self.terminal_output = QTextEdit()
        self.terminal_output.setReadOnly(True)
        self.terminal_output.setPlainText("FIELD//OS TERMINAL // READY\nCommands execute only when you press RUN.\n")
        layout.addWidget(self.terminal_output, 1)
        row = QHBoxLayout()
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Enter local shell command")
        self.command_input.returnPressed.connect(self.run_terminal_command)
        run = QPushButton("RUN")
        run.clicked.connect(self.run_terminal_command)
        clear = QPushButton("CLEAR")
        clear.clicked.connect(self.terminal_output.clear)
        stop = QPushButton("STOP")
        stop.clicked.connect(self.stop_terminal_command)
        row.addWidget(self.command_input, 1)
        row.addWidget(run)
        row.addWidget(stop)
        row.addWidget(clear)
        layout.addLayout(row)
        self._add_back(layout)
        return page

    def _build_system_page(self) -> QWidget:
        page, layout = self._page_shell("SYSTEM", "RVN-01 hardware and readiness")
        self.system_status = QLabel()
        self.system_status.setObjectName("body")
        self.system_status.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.system_status, 1)
        refresh = QPushButton("REFRESH SYSTEM")
        refresh.clicked.connect(self.refresh_local_state)
        layout.addWidget(refresh)
        self._add_back(layout)
        return page

    def refresh_local_state(self) -> None:
        host = socket.gethostname()
        ip = _primary_ip()
        self.system_status.setText(
            f"HOST        {host}\n"
            f"OS          {platform.system()} {platform.release()}\n"
            f"MACHINE     {platform.machine()}\n"
            f"PYTHON      {platform.python_version()}\n"
            f"CPU TEMP    {_read_cpu_temp()}\n"
            f"MEMORY      {_read_memory()}\n"
            f"STORAGE     {_storage_summary()}\n"
            f"UPTIME      {_read_uptime()}\n"
            f"PRIMARY IP  {ip}\n"
            "GPS         --\nMESH        --\nSDR         --"
        )
        self.network_status.setText(
            f"HOST        {host}\nPRIMARY IP  {ip}\n\n"
            "MODE        LOCAL VISIBILITY\n"
            "NEXT        interfaces / routes / neighbours / approved discovery"
        )
        home = Path.home()
        try:
            names = sorted(item.name for item in home.iterdir())[:12]
            listing = "\n".join(f"  {name}" for name in names) or "  --"
        except OSError:
            listing = "  unavailable"
        self.files_status.setText(
            f"HOME        {home}\nSTORAGE     {_storage_summary()}\n\nRECENT ROOT ENTRIES\n{listing}"
        )

    def run_terminal_command(self) -> None:
        command = self.command_input.text().strip()
        if not command:
            return
        if self.command_process is not None and self.command_process.state() != QProcess.ProcessState.NotRunning:
            self.terminal_output.append("BUSY // stop the current command first")
            return
        self.terminal_output.append(f"\nrvn@fieldos $ {command}")
        self.command_input.clear()
        process = QProcess(self)
        self.command_process = process
        process.setWorkingDirectory(str(Path.home()))
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        process.readyReadStandardOutput.connect(self._terminal_read)
        process.finished.connect(self._terminal_finished)
        if sys.platform.startswith("win"):
            process.start("powershell.exe", ["-NoProfile", "-Command", command])
        else:
            process.start("/bin/sh", ["-lc", command])

    def _terminal_read(self) -> None:
        if self.command_process is None:
            return
        text = bytes(self.command_process.readAllStandardOutput()).decode(errors="replace")
        if text:
            self.terminal_output.moveCursor(self.terminal_output.textCursor().MoveOperation.End)
            self.terminal_output.insertPlainText(text)
            self.terminal_output.ensureCursorVisible()

    def _terminal_finished(self, exit_code: int, _status) -> None:
        self.terminal_output.append(f"[exit {exit_code}] // command complete")

    def stop_terminal_command(self) -> None:
        if self.command_process is not None and self.command_process.state() != QProcess.ProcessState.NotRunning:
            self.command_process.terminate()
            self.terminal_output.append("INTERRUPT // terminate requested")

    def _tick(self) -> None:
        self.top.setText(f"RAVEN // RVN-01     FIELD//OS 2.2 DEV     {datetime.now().strftime('%H:%M:%S')}")

    def open_app(self, name: str) -> None:
        if name in {"SYSTEM", "NETWORK", "FILES"}:
            self.refresh_local_state()
        self.stack.setCurrentWidget(self.pages[name])
        self.footer.setText(f"RVN-01 // {name} // ESC = APPLICATIONS")
        if name == "TERMINAL":
            self.command_input.setFocus()

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
    print("FIELD//OS V2.2 DEV // PySide6 startup", flush=True)
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
