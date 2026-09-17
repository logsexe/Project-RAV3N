from __future__ import annotations

import os
import platform
import shutil
import socket
import sys
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QPointF, QProcess, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFontDatabase, QKeyEvent, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsDropShadowEffect,
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

from fieldos import theme
from fieldos.live_services import gpsd_fix, meshtastic_state, radio_state, system_metrics, zim_files
from fieldos.service_registry import capability_text, services_for

_FONTS_LOADED = False


def load_bundled_fonts() -> None:
    """Register fieldos/assets/fonts/*.ttf with Qt, once per process.

    Safe to call from every tier's main(): idempotent (guarded so a second
    call is a no-op) and fails silently if the file is missing or the
    platform's font backend rejects it — theme.MONO_FONT lists it first in
    an ordinary CSS-style font-family fallback stack, so if registration
    never happens the UI just renders in the next font in that stack
    (DejaVu Sans Mono / Consolas / Courier New) instead of erroring.
    """
    global _FONTS_LOADED
    if _FONTS_LOADED:
        return
    _FONTS_LOADED = True
    font_path = Path(__file__).parent / "assets" / "fonts" / "ShareTechMono-Regular.ttf"
    try:
        QFontDatabase.addApplicationFont(str(font_path))
    except Exception:
        pass


def apply_glow(widget: QWidget, color: str = theme.ACCENT, blur: float = 16.0) -> QGraphicsDropShadowEffect:
    """Soft phosphor-glow drop shadow. Qt's QSS has no text-shadow/box-shadow
    equivalent, so this is done in code via QGraphicsEffect, not stylesheet."""
    effect = QGraphicsDropShadowEffect(widget)
    effect.setColor(QColor(color))
    effect.setBlurRadius(blur)
    effect.setOffset(0, 0)
    widget.setGraphicsEffect(effect)
    return effect


def draw_tile_icon(kind: str, size: int = 28, color: str = theme.ACCENT) -> QPixmap:
    """Hand-drawn outline icon for a launcher tile.

    Drawn with QPainter primitives rather than bundling an icon font or
    image assets, matching how MapCanvas/SpectrumCanvas already draw their
    surfaces in visual_surfaces.py -- no new dependency, no new licensing
    surface for a field-deployed offline build.
    """
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color), max(1.4, size * 0.06))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    s = float(size)

    if kind == "radio":
        p.drawEllipse(QPointF(s * 0.5, s * 0.64), s * 0.06, s * 0.06)
        p.drawLine(QPointF(s * 0.5, s * 0.58), QPointF(s * 0.5, s * 0.22))
        p.drawArc(QRectF(s * 0.3, s * 0.3, s * 0.4, s * 0.4), 35 * 16, 110 * 16)
        p.drawArc(QRectF(s * 0.16, s * 0.16, s * 0.68, s * 0.68), 35 * 16, 110 * 16)
    elif kind == "nav":
        path = QPainterPath()
        path.moveTo(s * 0.5, s * 0.12)
        path.cubicTo(s * 0.8, s * 0.12, s * 0.8, s * 0.5, s * 0.5, s * 0.86)
        path.cubicTo(s * 0.2, s * 0.5, s * 0.2, s * 0.12, s * 0.5, s * 0.12)
        p.drawPath(path)
        p.drawEllipse(QPointF(s * 0.5, s * 0.36), s * 0.11, s * 0.11)
    elif kind == "mesh":
        points = [(0.5, 0.14), (0.83, 0.34), (0.83, 0.68), (0.5, 0.88), (0.17, 0.68), (0.17, 0.34)]
        for x, y in points:
            p.drawLine(QPointF(s * 0.5, s * 0.5), QPointF(s * x, s * y))
        for x, y in points:
            p.drawEllipse(QPointF(s * x, s * y), s * 0.06, s * 0.06)
        p.drawEllipse(QPointF(s * 0.5, s * 0.5), s * 0.05, s * 0.05)
    elif kind == "network":
        p.drawEllipse(QRectF(s * 0.12, s * 0.12, s * 0.76, s * 0.76))
        p.drawEllipse(QRectF(s * 0.34, s * 0.12, s * 0.32, s * 0.76))
        p.drawLine(QPointF(s * 0.14, s * 0.5), QPointF(s * 0.86, s * 0.5))
    elif kind == "ops":
        p.drawRoundedRect(QRectF(s * 0.22, s * 0.16, s * 0.56, s * 0.72), s * 0.06, s * 0.06)
        for y in (0.38, 0.52, 0.66):
            p.drawLine(QPointF(s * 0.34, s * y), QPointF(s * 0.66, s * y))
    elif kind == "library":
        p.drawRoundedRect(QRectF(s * 0.18, s * 0.16, s * 0.64, s * 0.68), s * 0.05, s * 0.05)
        p.drawLine(QPointF(s * 0.5, s * 0.16), QPointF(s * 0.5, s * 0.84))
    elif kind == "files":
        path = QPainterPath()
        path.moveTo(s * 0.15, s * 0.28)
        path.lineTo(s * 0.42, s * 0.28)
        path.lineTo(s * 0.5, s * 0.37)
        path.lineTo(s * 0.85, s * 0.37)
        path.lineTo(s * 0.85, s * 0.76)
        path.lineTo(s * 0.15, s * 0.76)
        path.closeSubpath()
        p.drawPath(path)
    elif kind == "terminal":
        p.drawRoundedRect(QRectF(s * 0.14, s * 0.2, s * 0.72, s * 0.6), s * 0.06, s * 0.06)
        p.drawLine(QPointF(s * 0.27, s * 0.4), QPointF(s * 0.39, s * 0.5))
        p.drawLine(QPointF(s * 0.39, s * 0.5), QPointF(s * 0.27, s * 0.6))
        p.drawLine(QPointF(s * 0.47, s * 0.6), QPointF(s * 0.63, s * 0.6))
    else:  # "system"
        p.drawRoundedRect(QRectF(s * 0.3, s * 0.3, s * 0.4, s * 0.4), s * 0.03, s * 0.03)
        for pos in (0.24, 0.5, 0.76):
            p.drawLine(QPointF(s * pos, s * 0.1), QPointF(s * pos, s * 0.3))
            p.drawLine(QPointF(s * pos, s * 0.7), QPointF(s * pos, s * 0.9))
            p.drawLine(QPointF(s * 0.1, s * pos), QPointF(s * 0.3, s * pos))
            p.drawLine(QPointF(s * 0.7, s * pos), QPointF(s * 0.9, s * pos))
    p.end()
    return pixmap


def build_tile_button(name: str, kind: str, desc: str) -> QPushButton:
    """Launcher tile: hand-drawn icon + a two-tone title/subtitle stack.

    A plain single-string QPushButton can't give the subtitle its own
    (dimmer, smaller) color via QSS, so the tile is a QPushButton carrying
    a child layout of separately styled labels instead -- QPushButton stays
    the clickable/hoverable/focusable widget (background, border, radius,
    hover state all still come from the #appCard QSS rule), the labels
    just render its content. QLabel doesn't grab mouse events by default,
    so clicks still reach the button underneath.
    """
    button = QPushButton()
    button.setObjectName("appCard")
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setMinimumHeight(88)
    button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    row = QHBoxLayout(button)
    row.setContentsMargins(14, 10, 10, 10)
    row.setSpacing(12)
    icon = QLabel()
    icon.setPixmap(draw_tile_icon(kind, 26))
    icon.setFixedSize(26, 26)
    row.addWidget(icon)
    text = QVBoxLayout()
    text.setSpacing(2)
    title = QLabel(name)
    title.setStyleSheet(f"color:{theme.TEXT_BRIGHT}; font-weight:500; font-size:14px; background:transparent;")
    subtitle = QLabel(desc)
    subtitle.setStyleSheet(f"color:{theme.TEXT_DIM}; font-size:11px; background:transparent;")
    text.addWidget(title)
    text.addWidget(subtitle)
    row.addLayout(text, 1)
    return button

APPS = (
    ("RADIO", "Receive-only RF"),
    ("MAP", "Offline navigation"),
    ("MESH", "Meshtastic"),
    ("TAK", "Situational awareness"),
    ("NETWORK", "Local diagnostics"),
    ("INTEL", "Operations / evidence"),
    ("LIBRARY", "Offline knowledge"),
    ("FILES", "Local storage"),
    ("TERMINAL", "Operator shell"),
    ("SYSTEM", "RVN-01 status"),
)

# Chrome (navigation, buttons, headings, tile titles) reads in UI_FONT, a
# system sans stack; actual data/telemetry (status readouts, lists, typed
# input, the top bar/footer) stays in MONO_FONT so the app still reads as
# an instrument rather than a generic app -- a common split in modern
# dashboards (Grafana/Datadog-style: sans chrome, monospace data).
STYLE = f"""
QWidget {{ background:{theme.BG}; color:{theme.TEXT}; font-family:{theme.UI_FONT}; font-size:14px; }}
QLabel#bar {{ background:{theme.PANEL}; color:{theme.ACCENT}; padding:9px 12px; font-family:{theme.MONO_FONT}; font-weight:700; letter-spacing:1px; }}
QLabel#hero {{ font-size:32px; font-weight:500; color:{theme.TEXT_BRIGHT}; letter-spacing:0.5px; }}
QLabel#title {{ font-size:22px; font-weight:500; color:{theme.TEXT_BRIGHT}; letter-spacing:0.5px; }}
QLabel#subtitle {{ color:{theme.TEXT_DIM}; }}
QLabel#body {{ color:{theme.TEXT}; font-family:{theme.MONO_FONT}; font-size:13px; }}
QPushButton {{ background:{theme.SURFACE}; border:1px solid {theme.BORDER_DIM}; border-radius:{theme.RADIUS}; padding:10px 14px; min-height:24px; font-family:{theme.UI_FONT}; font-size:14px; font-weight:500; }}
QPushButton:hover, QPushButton:focus {{ background:{theme.SURFACE_HOVER}; border:1px solid {theme.ACCENT}; }}
QPushButton:pressed {{ background:{theme.ACCENT_SOFT}; }}
QPushButton#primary {{ background:{theme.ACCENT_SOFT}; border:1px solid {theme.ACCENT}; color:{theme.TEXT_BRIGHT}; font-weight:700; }}
QPushButton#tile {{ min-height:68px; text-align:left; border-radius:{theme.RADIUS_LG}; }}
QLineEdit, QTextEdit {{ background:{theme.BG}; border:1px solid {theme.BORDER_DIM}; border-radius:{theme.RADIUS}; color:{theme.TEXT}; padding:8px 10px; font-family:{theme.MONO_FONT}; selection-background-color:{theme.ACCENT_SOFT}; }}
QLineEdit:focus, QTextEdit:focus {{ border:1px solid {theme.ACCENT}; }}
QScrollBar:vertical {{ background:{theme.BG}; width:10px; border:none; }}
QScrollBar::handle:vertical {{ background:{theme.BORDER_DIM}; min-height:24px; border-radius:5px; }}
QScrollBar::handle:vertical:hover {{ background:{theme.BORDER}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height:0px; }}
QSlider::groove:horizontal {{ background:{theme.BORDER_DIM}; height:4px; border-radius:2px; }}
QSlider::sub-page:horizontal {{ background:{theme.ACCENT}; height:4px; border-radius:2px; }}
QSlider::add-page:horizontal {{ background:{theme.BORDER_DIM}; height:4px; border-radius:2px; }}
QSlider::handle:horizontal {{ background:{theme.ACCENT}; border:2px solid {theme.BG}; width:14px; height:14px; margin:-6px 0; border-radius:8px; }}
QSlider::handle:horizontal:hover {{ background:{theme.TEXT_BRIGHT}; }}
"""


def _storage() -> str:
    try:
        usage = shutil.disk_usage(Path.home())
        return f"{usage.used / 1024**3:.1f}/{usage.total / 1024**3:.1f} GiB"
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
        self.executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="fieldos")
        self.futures: dict[str, Future] = {}

        shell = QWidget()
        root = QVBoxLayout(shell)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.top = QLabel(); self.top.setObjectName("bar"); root.addWidget(self.top)
        apply_glow(self.top)
        self.stack = QStackedWidget(); root.addWidget(self.stack, 1)
        self.footer = QLabel(); self.footer.setObjectName("bar"); root.addWidget(self.footer)
        apply_glow(self.footer, blur=12.0)
        self.setCentralWidget(shell)

        self.home = self._home()
        self.about = self._info(
            "ABOUT", "RAVEN // RVN-01",
            "FIELD//OS is the offline-first operator environment for RVN-01.\n\n"
            "The PySide6 shell stays lean while established upstream services provide GNSS, maps, SDR, mesh, TAK, offline knowledge and telemetry.",
        )
        self.contact = self._info(
            "CONTACT", "PROJECT RAVEN",
            "Repository: github.com/logsexe/Project-RAV3N\nNode: RVN-01\nPlatform: FIELD//OS V2\n\n"
            "No account or credential is required to enter FIELD//OS.",
        )
        self.launcher = self._launcher()
        for page in (self.home, self.about, self.contact, self.launcher):
            self.stack.addWidget(page)

        self.pages = {
            "RADIO": self._module_page("RADIO", "Receive-only RF workspace", True),
            "MAP": self._module_page("MAP", "Offline navigation and GNSS", True),
            "MESH": self._module_page("MESH", "Meshtastic nodes and messages"),
            "TAK": self._module_page("TAK", "Situational awareness / CoT"),
            "NETWORK": self._network_page(),
            "INTEL": self._simple_page("INTEL", "Operations, evidence and timeline", "ACTIVE OPERATION   LOCAL\nASSETS             0\nEVIDENCE           0\nEVENTS             0\n\nLightweight V2 operation store will live here."),
            "LIBRARY": self._module_page("LIBRARY", "Offline field knowledge"),
            "FILES": self._files_page(),
            "TERMINAL": self._terminal_page(),
            "SYSTEM": self._system_page(),
        }
        for page in self.pages.values():
            self.stack.addWidget(page)

        self.clock_timer = QTimer(self); self.clock_timer.timeout.connect(self._tick); self.clock_timer.start(1000)
        self.state_timer = QTimer(self); self.state_timer.timeout.connect(self.refresh_local_state); self.state_timer.start(3000)
        self.future_timer = QTimer(self); self.future_timer.timeout.connect(self._collect_futures); self.future_timer.start(150)
        self._tick(); self.refresh_local_state(); self.refresh_services(); self.show_home()

    def _shell(self, title: str, subtitle: str) -> tuple[QWidget, QVBoxLayout]:
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(22, 14, 22, 14); layout.setSpacing(8)
        heading = QLabel(title); heading.setObjectName("title"); layout.addWidget(heading)
        sub = QLabel(subtitle); sub.setObjectName("subtitle"); layout.addWidget(sub)
        return page, layout

    def _back(self, layout: QVBoxLayout) -> None:
        button = QPushButton("< APPLICATIONS"); button.clicked.connect(self.show_launcher); layout.addWidget(button)

    def _home(self) -> QWidget:
        page = QWidget(); layout = QVBoxLayout(page); layout.setContentsMargins(42, 30, 42, 30); layout.setSpacing(12); layout.addStretch()
        brand = QLabel("RAVEN"); brand.setObjectName("hero"); brand.setAlignment(Qt.AlignmentFlag.AlignCenter); layout.addWidget(brand)
        title = QLabel("FIELD//OS"); title.setObjectName("title"); title.setAlignment(Qt.AlignmentFlag.AlignCenter); layout.addWidget(title)
        sub = QLabel("RVN-01 // PORTABLE FIELD COMPUTER"); sub.setObjectName("subtitle"); sub.setAlignment(Qt.AlignmentFlag.AlignCenter); layout.addWidget(sub)
        enter = QPushButton("ENTER FIELD//OS"); enter.setObjectName("primary"); enter.clicked.connect(self.show_launcher); layout.addWidget(enter)
        row = QHBoxLayout(); about = QPushButton("ABOUT"); about.clicked.connect(lambda: self.stack.setCurrentWidget(self.about)); contact = QPushButton("CONTACT"); contact.clicked.connect(lambda: self.stack.setCurrentWidget(self.contact)); row.addWidget(about); row.addWidget(contact); layout.addLayout(row); layout.addStretch()
        return page

    def _info(self, title: str, subtitle: str, text: str) -> QWidget:
        page, layout = self._shell(title, subtitle); body = QLabel(text); body.setObjectName("body"); body.setWordWrap(True); body.setAlignment(Qt.AlignmentFlag.AlignTop); layout.addWidget(body, 1)
        back = QPushButton("< HOME"); back.clicked.connect(self.show_home); layout.addWidget(back); return page

    def _launcher(self) -> QWidget:
        page, layout = self._shell("APPLICATIONS", "Select a FIELD//OS module")
        grid = QGridLayout(); grid.setSpacing(8); self.buttons = []
        for i, (name, desc) in enumerate(APPS):
            button = QPushButton(f"{name}\n{desc}"); button.setObjectName("tile"); button.clicked.connect(lambda checked=False, n=name: self.open_app(n)); grid.addWidget(button, i // 4, i % 4); self.buttons.append(button)
        layout.addLayout(grid, 1); home = QPushButton("< HOME"); home.clicked.connect(self.show_home); layout.addWidget(home); return page

    def _module_page(self, module: str, subtitle: str, launchable: bool = False) -> QWidget:
        page, layout = self._shell(module, subtitle)
        label = QLabel(); label.setObjectName("body"); label.setAlignment(Qt.AlignmentFlag.AlignTop); label.setWordWrap(True); setattr(self, f"{module.lower()}_status", label); layout.addWidget(label, 1)
        row = QHBoxLayout(); refresh = QPushButton("REFRESH"); refresh.clicked.connect(lambda checked=False, m=module: self.refresh_module(m)); row.addWidget(refresh)
        if launchable:
            launch = QPushButton("OPEN AVAILABLE TOOL"); launch.clicked.connect(lambda checked=False, m=module: self.launch_first_service(m)); row.addWidget(launch)
        layout.addLayout(row); self._back(layout); return page

    def _simple_page(self, title: str, subtitle: str, text: str) -> QWidget:
        page, layout = self._shell(title, subtitle); body = QLabel(text); body.setObjectName("body"); body.setAlignment(Qt.AlignmentFlag.AlignTop); body.setWordWrap(True); layout.addWidget(body, 1); self._back(layout); return page

    def _network_page(self) -> QWidget:
        page, layout = self._shell("NETWORK", "Local diagnostics and inventory"); self.network_status = QLabel(); self.network_status.setObjectName("body"); self.network_status.setAlignment(Qt.AlignmentFlag.AlignTop); layout.addWidget(self.network_status, 1); refresh = QPushButton("REFRESH LOCAL STATE"); refresh.clicked.connect(self.refresh_local_state); layout.addWidget(refresh); self._back(layout); return page

    def _files_page(self) -> QWidget:
        page, layout = self._shell("FILES", "Local operation storage"); self.files_status = QLabel(); self.files_status.setObjectName("body"); self.files_status.setAlignment(Qt.AlignmentFlag.AlignTop); layout.addWidget(self.files_status, 1); refresh = QPushButton("REFRESH DIRECTORY"); refresh.clicked.connect(self.refresh_local_state); layout.addWidget(refresh); self._back(layout); return page

    def _terminal_page(self) -> QWidget:
        page, layout = self._shell("TERMINAL", "Operator-controlled local shell"); self.terminal_output = QTextEdit(); self.terminal_output.setReadOnly(True); self.terminal_output.setPlainText("FIELD//OS TERMINAL // READY\nCommands execute only when you press RUN.\n"); layout.addWidget(self.terminal_output, 1)
        row = QHBoxLayout(); self.command_input = QLineEdit(); self.command_input.setPlaceholderText("Enter local shell command"); self.command_input.returnPressed.connect(self.run_terminal_command); row.addWidget(self.command_input, 1)
        for text, slot in (("RUN", self.run_terminal_command), ("STOP", self.stop_terminal_command), ("CLEAR", self.terminal_output.clear)):
            button = QPushButton(text); button.clicked.connect(slot); row.addWidget(button)
        layout.addLayout(row); self._back(layout); return page

    def _system_page(self) -> QWidget:
        page, layout = self._shell("SYSTEM", "RVN-01 hardware and readiness"); self.system_status = QLabel(); self.system_status.setObjectName("body"); self.system_status.setAlignment(Qt.AlignmentFlag.AlignTop); layout.addWidget(self.system_status, 1); refresh = QPushButton("REFRESH SYSTEM"); refresh.clicked.connect(self.refresh_local_state); layout.addWidget(refresh); self._back(layout); return page

    def _submit(self, key: str, fn) -> None:
        future = self.futures.get(key)
        if future is None or future.done():
            self.futures[key] = self.executor.submit(fn)

    def refresh_services(self) -> None:
        self.refresh_module("RADIO"); self.refresh_module("MAP"); self.refresh_module("MESH"); self.refresh_module("LIBRARY"); self.refresh_module("TAK")

    def refresh_module(self, module: str) -> None:
        label = getattr(self, f"{module.lower()}_status", None)
        if label is not None:
            label.setText(f"PROBING...\n\n{capability_text(module)}")
        if module == "RADIO": self._submit("RADIO", radio_state)
        elif module == "MAP": self._submit("MAP", gpsd_fix)
        elif module == "MESH": self._submit("MESH", meshtastic_state)
        elif module == "LIBRARY": self._submit("LIBRARY", zim_files)
        elif module == "TAK":
            self.tak_status.setText("COT         LOCAL-FIRST\nSERVER      OPTIONAL\n\n" + capability_text("TAK") + "\n\nNo position or event is published automatically.")

    def _collect_futures(self) -> None:
        for key, future in list(self.futures.items()):
            if not future.done():
                continue
            try:
                value = future.result()
            except Exception as exc:
                getattr(self, f"{key.lower()}_status").setText(f"ERROR       {type(exc).__name__}\n\n{capability_text(key)}")
                del self.futures[key]
                continue
            if key == "MAP":
                if value.latitude is not None and value.longitude is not None:
                    position = f"{value.latitude:.6f}, {value.longitude:.6f}"
                else:
                    position = "--"
                self.map_status.setText(
                    f"GPS         {value.state}\nPOSITION    {position}\nALTITUDE    {value.altitude if value.altitude is not None else '--'}\nSPEED       {value.speed if value.speed is not None else '--'}\nTRACK       {value.track if value.track is not None else '--'}\n\n{capability_text('MAP')}"
                )
            elif key == "MESH":
                self.mesh_status.setText(
                    f"LINK        {value.state}\nPORT        {value.port or '--'}\nNODES       {value.nodes if value.nodes is not None else '--'}\nTX          EXPLICIT OPERATOR ACTION\n\n{capability_text('MESH')}"
                )
            elif key == "RADIO":
                self.radio_status.setText(
                    f"DEVICE      {value.state}\nRTL-SDR     {'READY' if value.rtl_sdr else 'NOT DETECTED'}\nGQRX        {'READY' if value.gqrx else 'NOT INSTALLED'}\nSDR++       {'READY' if value.sdrpp else 'NOT INSTALLED'}\nMODE        RECEIVE ONLY\n\n{capability_text('RADIO')}"
                )
            elif key == "LIBRARY":
                names = "\n".join(f"  {path.name}" for path in value[:8]) or "  --"
                self.library_status.setText(f"ZIM FILES   {len(value)}\n\nLOCAL COLLECTIONS\n{names}\n\n{capability_text('LIBRARY')}")
            del self.futures[key]

    def launch_first_service(self, module: str) -> None:
        allowed = {"qmapshack", "gqrx", "sdrpp"}
        for item in services_for(module):
            if item.key not in allowed or not item.detected():
                continue
            for exe in item.executables:
                path = shutil.which(exe)
                if path:
                    QProcess.startDetached(path, []); self.footer.setText(f"RVN-01 // {module} // LAUNCHED {item.label.upper()}"); return
        self.footer.setText(f"RVN-01 // {module} // NO EXTERNAL TOOL INSTALLED")

    def refresh_local_state(self) -> None:
        host, ip = socket.gethostname(), _primary_ip()
        metrics = system_metrics()
        self.system_status.setText(
            f"HOST        {host}\nOS          {platform.system()} {platform.release()}\nMACHINE     {platform.machine()}\nPYTHON      {platform.python_version()}\n"
            f"CPU         {metrics.get('CPU', '--')}\nTEMP        {metrics.get('TEMP', '--')}\nMEMORY      {metrics.get('MEMORY', '--')}\nSTORAGE     {metrics.get('STORAGE', _storage())}\nPRIMARY IP  {ip}\n\nSERVICES\n{capability_text('SYSTEM')}"
        )
        self.network_status.setText(f"HOST        {host}\nPRIMARY IP  {ip}\nMODE        LOCAL VISIBILITY\n\nNEXT        interfaces / routes / neighbours / approved discovery")
        home = Path.home()
        try: listing = "\n".join(f"  {p.name}" for p in sorted(home.iterdir(), key=lambda p: p.name)[:10]) or "  --"
        except OSError: listing = "  unavailable"
        self.files_status.setText(f"HOME        {home}\nSTORAGE     {_storage()}\n\nROOT ENTRIES\n{listing}")

    def run_terminal_command(self) -> None:
        command = self.command_input.text().strip()
        if not command: return
        if self.command_process and self.command_process.state() != QProcess.ProcessState.NotRunning:
            self.terminal_output.append("BUSY // stop current command first"); return
        self.terminal_output.append(f"\nrvn@fieldos $ {command}"); self.command_input.clear(); process = QProcess(self); self.command_process = process; process.setWorkingDirectory(str(Path.home())); process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels); process.readyReadStandardOutput.connect(self._terminal_read); process.finished.connect(self._terminal_finished)
        process.start("powershell.exe", ["-NoProfile", "-Command", command]) if sys.platform.startswith("win") else process.start("/bin/sh", ["-lc", command])

    def _terminal_read(self) -> None:
        if self.command_process:
            text = bytes(self.command_process.readAllStandardOutput()).decode(errors="replace")
            if text: self.terminal_output.insertPlainText(text); self.terminal_output.ensureCursorVisible()

    def _terminal_finished(self, exit_code: int, _status) -> None: self.terminal_output.append(f"[exit {exit_code}] // command complete")
    def stop_terminal_command(self) -> None:
        if self.command_process and self.command_process.state() != QProcess.ProcessState.NotRunning: self.command_process.terminate(); self.terminal_output.append("INTERRUPT // terminate requested")
    def _tick(self) -> None: self.top.setText(f"RAVEN // RVN-01     FIELD//OS 2.4 DEV     {datetime.now().strftime('%H:%M:%S')}")
    def open_app(self, name: str) -> None:
        if name in {"SYSTEM", "NETWORK", "FILES"}: self.refresh_local_state()
        elif name in {"RADIO", "MAP", "MESH", "TAK", "LIBRARY"}: self.refresh_module(name)
        self.stack.setCurrentWidget(self.pages[name]); self.footer.setText(f"RVN-01 // {name} // ESC = APPLICATIONS")
        if name == "TERMINAL": self.command_input.setFocus()
    def show_home(self) -> None: self.stack.setCurrentWidget(self.home); self.footer.setText("RVN-01 // FIELD//OS V2 // ENTER TO BEGIN")
    def show_launcher(self) -> None:
        self.stack.setCurrentWidget(self.launcher); self.footer.setText("RVN-01 // APPLICATIONS // ESC = HOME")
        if self.buttons: self.buttons[0].setFocus()
    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            current = self.stack.currentWidget()
            if current is self.launcher or current in {self.about, self.contact}: self.show_home()
            elif current is self.home: self.close()
            else: self.show_launcher()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event) -> None:
        # Every subclass adds its own QTimer(self) (radio_timer, v3_timer,
        # rvn_timer, ...); stop them all rather than naming each one here, so
        # none of them fire again and try to submit work to the executor
        # after it's shut down on the next line.
        for timer in self.findChildren(QTimer):
            timer.stop()
        self.executor.shutdown(wait=False, cancel_futures=True)
        super().closeEvent(event)


def _display_summary() -> str:
    return f"DISPLAY={os.environ.get('DISPLAY', '')!r} WAYLAND_DISPLAY={os.environ.get('WAYLAND_DISPLAY', '')!r} XDG_SESSION_TYPE={os.environ.get('XDG_SESSION_TYPE', '')!r}"


def main() -> int:
    print("FIELD//OS V2.4 DEV // PySide6 startup", flush=True); print(_display_summary(), flush=True)
    if sys.platform.startswith("linux") and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        print("FIELD//OS: no graphical display is available in this shell. Run from the RVN-01 desktop session or attach the active display session.", file=sys.stderr, flush=True); return 2
    app = QApplication.instance() or QApplication(sys.argv); load_bundled_fonts(); app.setStyleSheet(STYLE); window = FieldOSWindow(); window.show() if "--windowed" in sys.argv else window.showFullScreen(); print("FIELD//OS: Qt window created", flush=True); return app.exec()


if __name__ == "__main__": raise SystemExit(main())
