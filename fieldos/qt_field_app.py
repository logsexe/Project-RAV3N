from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QEvent, QProcess, Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .engine import OperationsEngine
from .live_services import meshtastic_nodes, network_interfaces, network_neighbours
from .maps import OfflineMapStore, Waypoint, bearing_distance
from .operations import OperationSessionManager
from .qt_map_radio_app import FieldOSWindow as V29FieldOSWindow
from .qt_app import STYLE, _display_summary
from .visual_surfaces import MapCanvas


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

def _human_size(num: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if num < 1024:
            return f"{num:.0f}{unit}" if unit == "B" else f"{num:.1f}{unit}"
        num /= 1024
    return f"{num:.1f}TB"


V29_STYLE = STYLE + """
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
QPushButton#appCard:hover, QPushButton#appCard:focus { background:#0d1c12; border:2px solid #63ff88; }
QPushButton#appCard:pressed { background:#14331d; }
"""


class FieldOSWindow(V29FieldOSWindow):
    """FIELD//OS V2.9 — efficient graphical RVN-01 field computer."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("RAVEN // FIELD//OS V2.9")
        self.pages["RVN-01"] = self.pages["SYSTEM"]
        self.tak_page = self.pages.get("TAK")

        self.operations = OperationSessionManager()
        self.ops_engine = OperationsEngine()
        old_intel = self.pages.pop("INTEL")
        index = self.stack.indexOf(old_intel)
        self.stack.removeWidget(old_intel)
        old_intel.deleteLater()
        ops_page = self._ops_page()
        self.stack.insertWidget(index, ops_page)
        self.pages["OPS"] = ops_page
        self._populate_operations()
        self._refresh_ops()

        self.map_store = OfflineMapStore()
        self._waypoints_cache: list[Waypoint] = []
        self._replace_page("MAP", self._navigation_page())
        self.pages["NAVIGATION"] = self.pages["MAP"]
        self._refresh_waypoints()

        self._replace_page("NETWORK", self._network_ops_page())
        self._replace_page("MESH", self._mesh_ops_page())
        self.refresh_local_state()

        self.files_current_dir = Path.home()
        self._replace_page("FILES", self._files_browser_page())
        self._files_navigate(self.files_current_dir)

        self.terminal_cwd = Path.home()
        self.terminal_history: list[str] = []
        self.terminal_history_index = 0
        self._replace_page("TERMINAL", self._terminal_ops_page())

        old_launcher = self.launcher
        index = self.stack.indexOf(old_launcher)
        self.stack.removeWidget(old_launcher)
        old_launcher.deleteLater()
        self.launcher = self._field_launcher()
        self.stack.insertWidget(index, self.launcher)

        self._rename_page("RVN-01", "RVN-01", "System // hardware // storage // power // services")

    def _ops_page(self) -> QWidget:
        page, layout = self._shell("OPS", "Active operation // notes // assets // evidence // timeline")

        op_row = QHBoxLayout()
        self.ops_selector = QComboBox()
        self.ops_selector.currentIndexChanged.connect(self._select_operation)
        op_row.addWidget(self.ops_selector, 1)
        new_op = QPushButton("NEW")
        new_op.clicked.connect(self._new_operation)
        op_row.addWidget(new_op)
        export_op = QPushButton("EXPORT")
        export_op.clicked.connect(self._export_operation)
        op_row.addWidget(export_op)
        layout.addLayout(op_row)

        self.ops_meta = QLabel("ASSETS --   EVIDENCE --   EVENTS --")
        self.ops_meta.setObjectName("subtitle")
        layout.addWidget(self.ops_meta)

        body = QHBoxLayout()
        left = QVBoxLayout()
        left.addWidget(QLabel("TIMELINE"))
        self.ops_timeline = QListWidget()
        left.addWidget(self.ops_timeline, 1)
        body.addLayout(left, 2)

        right = QVBoxLayout()
        right.addWidget(QLabel("ASSETS"))
        self.ops_assets = QListWidget()
        right.addWidget(self.ops_assets, 1)
        body.addLayout(right, 1)
        layout.addLayout(body, 1)

        note_row = QHBoxLayout()
        self.ops_note_input = QLineEdit()
        self.ops_note_input.setPlaceholderText("Add a timestamped note")
        self.ops_note_input.returnPressed.connect(self._add_ops_note)
        note_row.addWidget(self.ops_note_input, 1)
        add_note = QPushButton("ADD NOTE")
        add_note.clicked.connect(self._add_ops_note)
        note_row.addWidget(add_note)
        layout.addLayout(note_row)

        asset_row = QHBoxLayout()
        self.ops_asset_kind = QLineEdit()
        self.ops_asset_kind.setPlaceholderText("KIND (e.g. HOST)")
        self.ops_asset_value = QLineEdit()
        self.ops_asset_value.setPlaceholderText("VALUE")
        self.ops_asset_label = QLineEdit()
        self.ops_asset_label.setPlaceholderText("LABEL (optional)")
        for field in (self.ops_asset_kind, self.ops_asset_value, self.ops_asset_label):
            asset_row.addWidget(field, 1)
        add_asset = QPushButton("ADD ASSET")
        add_asset.clicked.connect(self._add_ops_asset)
        asset_row.addWidget(add_asset)
        layout.addLayout(asset_row)

        self._back(layout)
        return page

    def _populate_operations(self) -> None:
        self.ops_selector.blockSignals(True)
        self.ops_selector.clear()
        for session in self.operations.sessions:
            self.ops_selector.addItem(f"{session.id} — {session.name}")
        self.ops_selector.setCurrentIndex(self.operations.active_index)
        self.ops_selector.blockSignals(False)

    def _select_operation(self, index: int) -> None:
        if index < 0:
            return
        self.operations.select(index)
        self._refresh_ops()

    def _new_operation(self) -> None:
        name, ok = QInputDialog.getText(self, "NEW OPERATION", "Operation name:")
        if not ok or not name.strip():
            return
        self.operations.create(name.strip())
        self._populate_operations()
        self._refresh_ops()

    def _export_operation(self) -> None:
        try:
            archive = self.operations.export_active()
        except OSError as exc:
            self.footer.setText(f"RVN-01 // OPS // EXPORT FAILED // {type(exc).__name__}")
            return
        self.footer.setText(f"RVN-01 // OPS // EXPORTED // {archive.name}")

    def _add_ops_note(self) -> None:
        text = self.ops_note_input.text().strip()
        if not text:
            return
        self.operations.add_note(text)
        self.ops_note_input.clear()
        self._refresh_ops()

    def _add_ops_asset(self) -> None:
        kind = self.ops_asset_kind.text().strip()
        value = self.ops_asset_value.text().strip()
        label = self.ops_asset_label.text().strip()
        if not kind or not value:
            self.footer.setText("RVN-01 // OPS // ASSET NEEDS KIND AND VALUE")
            return
        self.ops_engine.upsert_asset(self.operations.active.id, kind, value, label=label)
        self.ops_asset_kind.clear()
        self.ops_asset_value.clear()
        self.ops_asset_label.clear()
        self._refresh_ops()

    def _refresh_ops(self) -> None:
        operation_id = self.operations.active.id
        assets = self.ops_engine.list_assets(operation_id)
        evidence = self.ops_engine.list_evidence(operation_id)
        events = self.ops_engine.timeline(operation_id, limit=50)
        self.ops_meta.setText(
            f"OPERATION {operation_id}   ASSETS {len(assets)}   EVIDENCE {len(evidence)}   EVENTS {len(events)}"
        )
        self.ops_timeline.clear()
        for event in events:
            self.ops_timeline.addItem(f"{event.timestamp}  {event.event_type:<10} {event.summary}")
        self.ops_assets.clear()
        for asset in assets:
            self.ops_assets.addItem(f"[{asset.kind}] {asset.label}")

    def _network_ops_page(self) -> QWidget:
        page, layout = self._shell("NETWORK", "Local interfaces // neighbours // authorised diagnostics")
        self.network_status = QLabel("HOST        PROBING")
        self.network_status.setObjectName("body")
        layout.addWidget(self.network_status)

        body = QHBoxLayout()
        left = QVBoxLayout()
        left.addWidget(QLabel("INTERFACES"))
        self.network_interfaces_list = QListWidget()
        left.addWidget(self.network_interfaces_list, 1)
        body.addLayout(left, 1)

        right = QVBoxLayout()
        right.addWidget(QLabel("NEIGHBOURS (ARP/ND)"))
        self.network_neighbours_list = QListWidget()
        right.addWidget(self.network_neighbours_list, 1)
        body.addLayout(right, 1)
        layout.addLayout(body, 1)

        refresh = QPushButton("REFRESH LOCAL STATE")
        refresh.clicked.connect(self.refresh_local_state)
        layout.addWidget(refresh)
        self._back(layout)
        return page

    def refresh_local_state(self) -> None:
        super().refresh_local_state()
        if hasattr(self, "network_interfaces_list"):
            self._refresh_network_details()

    def _refresh_network_details(self) -> None:
        self.network_interfaces_list.clear()
        interfaces = network_interfaces()
        if not interfaces:
            self.network_interfaces_list.addItem("NO INTERFACES REPORTED")
        for iface in interfaces:
            address = iface.address or "--"
            self.network_interfaces_list.addItem(f"{iface.name:<10} {iface.state:<12} {address}")

        self.network_neighbours_list.clear()
        neighbours = network_neighbours()
        if not neighbours:
            self.network_neighbours_list.addItem("NO NEIGHBOURS REPORTED")
        for neighbour in neighbours:
            lladdr = neighbour.lladdr or "--"
            self.network_neighbours_list.addItem(f"{neighbour.address:<16} {lladdr:<18} {neighbour.device} {neighbour.state}")

    def _mesh_ops_page(self) -> QWidget:
        page, layout = self._shell("MESH", "Meshtastic nodes // operator-controlled messaging")
        self.mesh_status = QLabel("LINK        PROBING")
        self.mesh_status.setObjectName("body")
        layout.addWidget(self.mesh_status)

        layout.addWidget(QLabel("NODES"))
        self.mesh_nodes_list = QListWidget()
        layout.addWidget(self.mesh_nodes_list, 1)

        refresh = QPushButton("REFRESH")
        refresh.clicked.connect(lambda: self.refresh_module("MESH"))
        layout.addWidget(refresh)
        self._back(layout)
        return page

    def refresh_module(self, module: str) -> None:
        super().refresh_module(module)
        if module == "MESH":
            self._submit("MESHNODES", meshtastic_nodes)

    def _collect_futures(self) -> None:
        mesh_nodes_future = self.futures.get("MESHNODES")
        mesh_nodes_value = None
        if mesh_nodes_future is not None and mesh_nodes_future.done():
            try:
                mesh_nodes_value = mesh_nodes_future.result()
            except Exception:
                mesh_nodes_value = ()
        super()._collect_futures()
        if mesh_nodes_value is not None:
            self.mesh_nodes_list.clear()
            if mesh_nodes_value:
                for node in mesh_nodes_value:
                    last_heard = node.last_heard or "--"
                    self.mesh_nodes_list.addItem(f"{node.name:<20} {node.id:<12} LAST {last_heard}")
            else:
                self.mesh_nodes_list.addItem("NO NODES REPORTED")

    def _navigation_page(self) -> QWidget:
        page, layout = self._shell("NAVIGATION", "Offline map // live GNSS overlay // waypoints")
        self.map_canvas = MapCanvas()
        layout.addWidget(self.map_canvas, 2)
        self.map_status = QLabel("GPS         PROBING")
        self.map_status.setObjectName("body")
        layout.addWidget(self.map_status)

        body = QHBoxLayout()
        self.waypoints_list = QListWidget()
        self.waypoints_list.currentRowChanged.connect(self._show_waypoint_detail)
        body.addWidget(self.waypoints_list, 1)
        self.waypoint_detail = QLabel("SELECT A WAYPOINT")
        self.waypoint_detail.setObjectName("body")
        self.waypoint_detail.setWordWrap(True)
        body.addWidget(self.waypoint_detail, 1)
        layout.addLayout(body, 1)

        row = QHBoxLayout()
        add_wp = QPushButton("ADD WAYPOINT (CURRENT FIX)")
        add_wp.clicked.connect(self._add_waypoint)
        row.addWidget(add_wp)
        refresh = QPushButton("REFRESH GPS")
        refresh.clicked.connect(lambda: self.refresh_module("MAP"))
        row.addWidget(refresh)
        companion = QPushButton("OPEN QMAPSHACK")
        companion.clicked.connect(lambda: self.launch_first_service("MAP"))
        row.addWidget(companion)
        layout.addLayout(row)
        self._back(layout)
        return page

    def _refresh_waypoints(self) -> None:
        self._waypoints_cache = self.map_store.waypoints()
        self.waypoints_list.clear()
        for wp in self._waypoints_cache:
            self.waypoints_list.addItem(f"{wp.id}  {wp.label}  ({wp.latitude:.5f}, {wp.longitude:.5f})")
        self.map_canvas.set_waypoints([(wp.latitude, wp.longitude, wp.label) for wp in self._waypoints_cache])

    def _show_waypoint_detail(self, row: int) -> None:
        if row < 0 or row >= len(self._waypoints_cache):
            self.waypoint_detail.setText("SELECT A WAYPOINT")
            return
        wp = self._waypoints_cache[row]
        if self.map_canvas.latitude is not None and self.map_canvas.longitude is not None:
            distance_m, bearing_deg = bearing_distance(
                self.map_canvas.latitude, self.map_canvas.longitude, wp.latitude, wp.longitude
            )
            range_text = f"{distance_m:.0f} m @ {bearing_deg:.0f}° FROM CURRENT FIX"
        else:
            range_text = "NO CURRENT FIX // RANGE UNAVAILABLE"
        self.waypoint_detail.setText(
            f"{wp.label}\n\nID          {wp.id}\nLAT         {wp.latitude:.6f}\nLON         {wp.longitude:.6f}\n"
            f"CREATED     {wp.created_at}\nOPERATION   {wp.operation_id or '--'}\n\n{range_text}"
        )

    def _add_waypoint(self) -> None:
        if self.map_canvas.latitude is None or self.map_canvas.longitude is None:
            self.footer.setText("RVN-01 // NAVIGATION // NO GPS FIX // CANNOT ADD WAYPOINT")
            return
        label, ok = QInputDialog.getText(self, "ADD WAYPOINT", "Label:")
        if not ok or not label.strip():
            return
        item = self.map_store.add_waypoint(
            self.map_canvas.latitude, self.map_canvas.longitude, label.strip(), self.operations.active.id
        )
        self.ops_engine.record_event(
            self.operations.active.id,
            "WAYPOINT",
            f"{item.id} {item.label}",
            metadata={"lat": item.latitude, "lon": item.longitude},
        )
        self._refresh_waypoints()
        self.footer.setText(f"RVN-01 // NAVIGATION // WAYPOINT {item.id} ADDED")

    def _files_browser_page(self) -> QWidget:
        page, layout = self._shell("FILES", "Local storage // browse read-only")
        self.files_status = QLabel()
        self.files_status.setObjectName("body")
        layout.addWidget(self.files_status)

        self.files_path_label = QLabel()
        self.files_path_label.setObjectName("subtitle")
        layout.addWidget(self.files_path_label)

        self.files_list = QListWidget()
        self.files_list.itemActivated.connect(self._open_files_entry)
        layout.addWidget(self.files_list, 1)

        row = QHBoxLayout()
        up = QPushButton("UP")
        up.clicked.connect(self._files_go_up)
        row.addWidget(up)
        home = QPushButton("HOME")
        home.clicked.connect(lambda: self._files_navigate(Path.home()))
        row.addWidget(home)
        op_folder = QPushButton("OPERATION FOLDER")
        op_folder.clicked.connect(lambda: self._files_navigate(self.operations.session_path()))
        row.addWidget(op_folder)
        refresh = QPushButton("REFRESH")
        refresh.clicked.connect(lambda: self._files_navigate(self.files_current_dir))
        row.addWidget(refresh)
        layout.addLayout(row)
        self._back(layout)
        return page

    def _files_navigate(self, path: Path) -> None:
        try:
            entries = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except OSError as exc:
            self.footer.setText(f"RVN-01 // FILES // {type(exc).__name__} // {path}")
            return
        self.files_current_dir = path
        self.files_path_label.setText(str(path))
        self.files_list.clear()
        for entry in entries[:300]:
            try:
                if entry.is_dir():
                    label = f"[DIR]  {entry.name}"
                else:
                    label = f"       {entry.name}  ({_human_size(entry.stat().st_size)})"
            except OSError:
                continue
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, str(entry))
            self.files_list.addItem(item)
        self.footer.setText(f"RVN-01 // FILES // {len(entries)} ENTRIES // {path}")

    def _open_files_entry(self, item: QListWidgetItem) -> None:
        target = Path(item.data(Qt.ItemDataRole.UserRole))
        if target.is_dir():
            self._files_navigate(target)
            return
        try:
            size = target.stat().st_size
        except OSError:
            self.footer.setText(f"RVN-01 // FILES // {target.name} // UNKNOWN SIZE")
            return
        self.footer.setText(f"RVN-01 // FILES // {target.name} // {_human_size(size)}")

    def _files_go_up(self) -> None:
        parent = self.files_current_dir.parent
        if parent != self.files_current_dir:
            self._files_navigate(parent)

    def _terminal_ops_page(self) -> QWidget:
        page, layout = self._shell("TERMINAL", "Operator-controlled local shell // captured to active operation")
        self.terminal_output = QTextEdit()
        self.terminal_output.setReadOnly(True)
        self.terminal_output.setPlainText(
            "FIELD//OS TERMINAL // READY\nCommands execute only when you press RUN. Output is captured into the active operation.\n"
        )
        layout.addWidget(self.terminal_output, 1)

        self.terminal_cwd_label = QLabel(str(self.terminal_cwd))
        self.terminal_cwd_label.setObjectName("subtitle")
        layout.addWidget(self.terminal_cwd_label)

        row = QHBoxLayout()
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Enter local shell command (Up/Down for history)")
        self.command_input.returnPressed.connect(self.run_terminal_command)
        self.command_input.installEventFilter(self)
        row.addWidget(self.command_input, 1)
        for text, slot in (("RUN", self.run_terminal_command), ("STOP", self.stop_terminal_command), ("CLEAR", self.terminal_output.clear)):
            button = QPushButton(text)
            button.clicked.connect(slot)
            row.addWidget(button)
        layout.addLayout(row)
        self._back(layout)
        return page

    def eventFilter(self, obj, event) -> bool:
        if obj is getattr(self, "command_input", None) and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Up:
                self._terminal_history_step(-1)
                return True
            if event.key() == Qt.Key.Key_Down:
                self._terminal_history_step(1)
                return True
        return super().eventFilter(obj, event)

    def _terminal_history_step(self, direction: int) -> None:
        if not self.terminal_history:
            return
        self.terminal_history_index = max(0, min(len(self.terminal_history) - 1, self.terminal_history_index + direction))
        self.command_input.setText(self.terminal_history[self.terminal_history_index])

    def run_terminal_command(self) -> None:
        command = self.command_input.text().strip()
        if not command:
            return
        if self.command_process and self.command_process.state() != QProcess.ProcessState.NotRunning:
            self.terminal_output.append("BUSY // stop current command first")
            return

        self.terminal_history.append(command)
        self.terminal_history_index = len(self.terminal_history)

        if command == "cd" or command.startswith("cd "):
            self._terminal_change_directory(command)
            return

        self.terminal_output.append(f"\nrvn@fieldos $ {command}")
        self.command_input.clear()
        self._terminal_command_text = command
        self._terminal_output_chunks: list[str] = []
        process = QProcess(self)
        self.command_process = process
        process.setWorkingDirectory(str(self.terminal_cwd))
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        process.readyReadStandardOutput.connect(self._terminal_read)
        process.finished.connect(self._terminal_finished)
        process.start("powershell.exe", ["-NoProfile", "-Command", command]) if sys.platform.startswith("win") else process.start("/bin/sh", ["-lc", command])

    def _terminal_change_directory(self, command: str) -> None:
        target = command[2:].strip() or str(Path.home())
        candidate = Path(target).expanduser()
        if not candidate.is_absolute():
            candidate = self.terminal_cwd / candidate
        if candidate.is_dir():
            self.terminal_cwd = candidate.resolve()
            self.terminal_cwd_label.setText(str(self.terminal_cwd))
            self.terminal_output.append(f"\nrvn@fieldos $ {command}")
        else:
            self.terminal_output.append(f"\nrvn@fieldos $ {command}\ncd: no such directory: {target}")
        self.command_input.clear()

    def _terminal_read(self) -> None:
        if self.command_process:
            text = bytes(self.command_process.readAllStandardOutput()).decode(errors="replace")
            if text:
                self.terminal_output.insertPlainText(text)
                self.terminal_output.ensureCursorVisible()
                self._terminal_output_chunks.append(text)

    def _terminal_finished(self, exit_code: int, _status) -> None:
        self.terminal_output.append(f"[exit {exit_code}] // command complete")
        output_lines = "".join(self._terminal_output_chunks).splitlines()
        try:
            self.operations.capture_command(self._terminal_command_text, output_lines, exit_code, "TERMINAL")
        except OSError as exc:
            self.footer.setText(f"RVN-01 // TERMINAL // CAPTURE FAILED // {type(exc).__name__}")
            return
        self.footer.setText(f"RVN-01 // TERMINAL // CAPTURED // {self.operations.active.id}")

    def _field_launcher(self) -> QWidget:
        page = QWidget(); page.setObjectName("fieldLauncher")
        layout = QVBoxLayout(page); layout.setContentsMargins(14, 8, 14, 8); layout.setSpacing(5)
        header = QLabel("RAVEN // RVN-01"); header.setObjectName("launcherBrand"); layout.addWidget(header)
        meta = QLabel("FIELD//OS 2.9   •   OFFLINE FIELD COMPUTER   •   SELECT APPLICATION"); meta.setObjectName("launcherMeta"); layout.addWidget(meta)
        grid = QGridLayout(); grid.setHorizontalSpacing(7); grid.setVerticalSpacing(7); grid.setContentsMargins(0, 3, 0, 2)
        self.buttons = []
        for i, (name, glyph, desc) in enumerate(FIELD_APPS):
            button = QPushButton(f"{glyph}   {name}\n      {desc}")
            button.setObjectName("appCard"); button.setCursor(Qt.CursorShape.PointingHandCursor); button.setMinimumHeight(88); button.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            button.clicked.connect(lambda checked=False, n=name: self.open_app(n)); grid.addWidget(button, i // 3, i % 3); self.buttons.append(button)
        layout.addLayout(grid, 1)
        hint = QLabel("TOUCH / ENTER OPEN   •   ESC APPLICATIONS   •   CTRL+Q EXIT"); hint.setObjectName("launcherHint"); hint.setAlignment(Qt.AlignmentFlag.AlignCenter); layout.addWidget(hint)
        return page

    def _rename_page(self, name: str, title: str, subtitle: str) -> None:
        page = self.pages[name]; labels = page.findChildren(QLabel)
        if labels: labels[0].setText(title)
        if len(labels) > 1: labels[1].setText(subtitle)

    def show_home(self) -> None:
        if hasattr(self, "launcher"): self.show_launcher()
        else: super().show_home()

    def open_app(self, name: str) -> None:
        page = self.pages.get(name)
        if page is None:
            self.footer.setText(f"RVN-01 // {name} // MODULE NOT PRESENT"); return
        self.stack.setCurrentWidget(page)
        self.footer.setText(f"RVN-01 // {name} // READY // ESC/BACK APPLICATIONS")
        if name == "NAVIGATION": self.refresh_module("MAP"); self._refresh_waypoints()
        elif name in {"RADIO", "MESH", "LIBRARY"}: self.refresh_module(name)
        elif name in {"NETWORK", "RVN-01"}: self.refresh_local_state()
        elif name == "OPS": self._refresh_ops()
        elif name == "FILES": self._files_navigate(self.files_current_dir)
        # Kick demand-driven adapters immediately on entry rather than waiting
        # for their low-frequency idle timers.
        if name == "RADIO": self.refresh_live_radio()
        elif name == "NAVIGATION": self.refresh_map_pack()

    def _tick(self) -> None:
        self.top.setText(f"RAVEN // RVN-01     FIELD//OS 2.9     GPS • MESH • NET • SDR •     {datetime.now().strftime('%H:%M:%S')}")


def main() -> int:
    print("FIELD//OS V2.9 // efficient graphical RVN-01 field computer", flush=True)
    print(_display_summary(), flush=True)
    if sys.platform.startswith("linux") and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        print("FIELD//OS: no graphical display is available in this shell.", file=sys.stderr, flush=True); return 2
    app = QApplication.instance() or QApplication(sys.argv); app.setStyleSheet(V29_STYLE)
    window = FieldOSWindow(); window.show() if "--windowed" in sys.argv else window.showFullScreen()
    print("FIELD//OS: V2.9 graphical field-computer window created", flush=True)
    return app.exec()


if __name__ == "__main__": raise SystemExit(main())
