from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QEvent, QProcess, Qt, Signal
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

from . import theme
from .engine import OperationsEngine
from .live_services import (
    meshtastic_nodes,
    monitor_mode_capable,
    network_interfaces,
    network_neighbours,
    open_meshtastic_interface,
    wifi_scan,
)
from .operations import OperationSessionManager
from .qt_map_radio_app import FieldOSWindow as V29FieldOSWindow
from .qt_app import STYLE, _display_summary, build_tile_button, load_bundled_fonts
from .visual_surfaces import MapCanvas


FIELD_APPS = (
    ("RADIO", "radio", "RX / SPECTRUM"),
    ("NAVIGATION", "nav", "MAP / GPS"),
    ("MESH", "mesh", "NODES / MESSAGES"),
    ("NETWORK", "network", "LOCAL / DEVICES"),
    ("OPS", "ops", "MISSION / EVIDENCE"),
    ("LIBRARY", "library", "OFFLINE KNOWLEDGE"),
    ("FILES", "files", "LOCAL STORAGE"),
    ("TERMINAL", "terminal", "OPERATOR SHELL"),
    ("RVN-01", "system", "SYSTEM / HARDWARE"),
)

def _human_size(num: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if num < 1024:
            return f"{num:.0f}{unit}" if unit == "B" else f"{num:.1f}{unit}"
        num /= 1024
    return f"{num:.1f}TB"


V29_STYLE = STYLE + f"""
QWidget#fieldLauncher {{ background:{theme.BG}; }}
QLabel#launcherBrand {{ color:{theme.TEXT_BRIGHT}; font-size:19px; font-weight:500; letter-spacing:1px; font-family:{theme.MONO_FONT}; }}
QLabel#launcherMeta {{ color:{theme.TEXT_FAINT}; font-size:11px; font-weight:500; letter-spacing:0.5px; }}
QLabel#launcherHint {{ color:{theme.TEXT_FAINT}; font-size:10px; }}
QPushButton#appCard {{
    background:{theme.SURFACE};
    color:{theme.TEXT_BRIGHT};
    border:1px solid {theme.BORDER_DIM};
    border-radius:{theme.RADIUS_LG};
    padding:12px 14px;
    text-align:left;
    font-family:{theme.UI_FONT};
    font-size:14px;
    font-weight:500;
    icon-size:26px;
}}
QPushButton#appCard:hover, QPushButton#appCard:focus {{ background:{theme.SURFACE_HOVER}; border:1px solid {theme.ACCENT}; }}
QPushButton#appCard:pressed {{ background:{theme.ACCENT_SOFT}; }}
"""


class FieldOSWindow(V29FieldOSWindow):
    """FIELD//OS V2.9 — efficient graphical RVN-01 field computer."""

    # Meshtastic's pubsub callback fires on the interface's own reader
    # thread. Qt signals are the safe way to cross into the UI thread: emit()
    # is thread-safe, and the connected slot below runs queued on the main
    # thread regardless of which thread emitted it.
    mesh_message_received = Signal(str, str, str)

    def __init__(self) -> None:
        # Set before super().__init__(): the base class's own __init__ calls
        # refresh_services() -> refresh_module("MESH") during its own
        # construction, and since `self` is this most-derived class, that
        # resolves to this class's override, which checks self.mesh_interface.
        self.mesh_interface = None
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

        self._replace_page("MAP", self._navigation_page())
        self.pages["NAVIGATION"] = self.pages["MAP"]

        self._replace_page("NETWORK", self._network_ops_page())
        self.mesh_message_received.connect(self._on_mesh_message)
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
        page, layout = self._shell("NETWORK", "Local interfaces // neighbours // authorised Wi-Fi recon")
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

        self.wifi_toggle = QPushButton("> WI-FI RECON")
        self.wifi_toggle.setCheckable(True)
        self.wifi_toggle.toggled.connect(self._toggle_wifi_panel)
        layout.addWidget(self.wifi_toggle)

        self.wifi_panel = QWidget()
        wifi_layout = QVBoxLayout(self.wifi_panel)
        wifi_layout.setContentsMargins(0, 0, 0, 0)
        wifi_layout.addWidget(QLabel("WI-FI NETWORKS"))
        self.network_wifi_list = QListWidget()
        wifi_layout.addWidget(self.network_wifi_list, 1)
        self.network_wifi_status = QLabel("MONITOR MODE   PROBING")
        self.network_wifi_status.setObjectName("subtitle")
        wifi_layout.addWidget(self.network_wifi_status)
        self.wifi_scan_button = QPushButton("SCAN WI-FI (SENDS PROBE REQUESTS)")
        self.wifi_scan_button.clicked.connect(self._scan_wifi)
        wifi_layout.addWidget(self.wifi_scan_button)
        self.wifi_panel.setVisible(False)
        layout.addWidget(self.wifi_panel, 1)

        refresh = QPushButton("REFRESH LOCAL STATE")
        refresh.clicked.connect(self.refresh_local_state)
        layout.addWidget(refresh)
        self._back(layout)
        return page

    def _toggle_wifi_panel(self, checked: bool) -> None:
        self.wifi_panel.setVisible(checked)
        self.wifi_toggle.setText(("v" if checked else ">") + " WI-FI RECON")

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

        monitor_ready = monitor_mode_capable()
        self.network_wifi_status.setText(
            f"MONITOR MODE   {'READY' if monitor_ready else 'NOT PRESENT'}   //   PASSIVE PACKET CAPTURE NOT YET IMPLEMENTED"
        )

    def _scan_wifi(self) -> None:
        if "WIFISCAN" in self.futures:
            return
        self.wifi_scan_button.setEnabled(False)
        self.network_wifi_list.clear()
        self.network_wifi_list.addItem("SCANNING...")
        self.footer.setText("RVN-01 // NETWORK // WI-FI SCAN // SENDING PROBE REQUESTS")
        self._submit("WIFISCAN", wifi_scan)

    def _mesh_ops_page(self) -> QWidget:
        page, layout = self._shell("MESH", "Meshtastic nodes // operator-controlled messaging")
        self.mesh_status = QLabel("LINK        PROBING")
        self.mesh_status.setObjectName("body")
        layout.addWidget(self.mesh_status)

        body = QHBoxLayout()
        left = QVBoxLayout()
        left.addWidget(QLabel("NODES"))
        self.mesh_nodes_list = QListWidget()
        left.addWidget(self.mesh_nodes_list, 1)
        body.addLayout(left, 1)

        right = QVBoxLayout()
        right.addWidget(QLabel("MESSAGES"))
        self.mesh_messages_list = QListWidget()
        right.addWidget(self.mesh_messages_list, 1)
        body.addLayout(right, 1)
        layout.addLayout(body, 1)

        connect_row = QHBoxLayout()
        self.mesh_connect_button = QPushButton("CONNECT")
        self.mesh_connect_button.clicked.connect(self._toggle_mesh_connection)
        connect_row.addWidget(self.mesh_connect_button)
        refresh = QPushButton("REFRESH")
        refresh.clicked.connect(lambda: self.refresh_module("MESH"))
        connect_row.addWidget(refresh)
        layout.addLayout(connect_row)

        message_row = QHBoxLayout()
        self.mesh_message_input = QLineEdit()
        self.mesh_message_input.setPlaceholderText("Broadcast text — CONNECT first")
        self.mesh_message_input.returnPressed.connect(self._send_mesh_message)
        message_row.addWidget(self.mesh_message_input, 1)
        send = QPushButton("SEND")
        send.clicked.connect(self._send_mesh_message)
        message_row.addWidget(send)
        layout.addLayout(message_row)

        self._back(layout)
        return page

    def refresh_module(self, module: str) -> None:
        if module == "MESH" and self.mesh_interface is not None:
            self._refresh_mesh_from_persistent()
            return
        super().refresh_module(module)
        if module == "MESH":
            self._submit("MESHNODES", meshtastic_nodes)

    def _refresh_mesh_from_persistent(self) -> None:
        """Read node state from the already-open connection instead of
        opening a second, competing one on the same serial port."""
        nodes = getattr(self.mesh_interface, "nodes", {}) or {}
        self.mesh_status.setText(
            f"LINK        CONNECTED (PERSISTENT)\nNODES       {len(nodes)}\nTX          EXPLICIT OPERATOR ACTION"
        )
        self.mesh_nodes_list.clear()
        if not nodes:
            self.mesh_nodes_list.addItem("NO NODES REPORTED")
            return
        for node_id, info in nodes.items():
            info = info if isinstance(info, dict) else {}
            user = info.get("user", {}) if isinstance(info.get("user"), dict) else {}
            name = user.get("longName") or user.get("shortName") or str(node_id)
            last_heard = info.get("lastHeard")
            self.mesh_nodes_list.addItem(f"{name:<20} {node_id:<12} LAST {last_heard or '--'}")

    def _toggle_mesh_connection(self) -> None:
        if self.mesh_interface is not None:
            self._disconnect_mesh()
            return
        self.mesh_connect_button.setEnabled(False)
        self.mesh_status.setText("LINK        CONNECTING...")
        self._submit("MESHCONNECT", open_meshtastic_interface)

    def _disconnect_mesh(self) -> None:
        if self.mesh_interface is None:
            return
        try:
            from pubsub import pub
            pub.unsubscribe(self._mesh_pubsub_callback, "meshtastic.receive")
        except Exception:
            pass
        try:
            self.mesh_interface.close()
        except Exception:
            pass
        self.mesh_interface = None
        self.mesh_connect_button.setText("CONNECT")
        self.mesh_status.setText("LINK        DISCONNECTED")
        self.footer.setText("RVN-01 // MESH // DISCONNECTED")

    def _mesh_pubsub_callback(self, packet=None, interface=None) -> None:
        """Runs on Meshtastic's reader thread. No Qt widget access here —
        only emit(), which is safe to call from any thread."""
        try:
            decoded = packet.get("decoded", {}) if isinstance(packet, dict) else {}
            if decoded.get("portnum") != "TEXT_MESSAGE_APP":
                return
            text = decoded.get("text") or ""
            sender_key = packet.get("fromId") or packet.get("from")
            sender_id = str(sender_key if sender_key is not None else "UNKNOWN")
            sender_name = sender_id
            nodes = getattr(interface, "nodes", {}) or {}
            info = nodes.get(sender_key) or nodes.get(sender_id)
            if isinstance(info, dict):
                user = info.get("user", {}) if isinstance(info.get("user"), dict) else {}
                sender_name = user.get("longName") or user.get("shortName") or sender_id
            self.mesh_message_received.emit(sender_id, sender_name, text)
        except Exception:
            pass

    def _on_mesh_message(self, sender_id: str, sender_name: str, text: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        self.mesh_messages_list.addItem(f"[{stamp}] {sender_name}: {text}")
        self.footer.setText(f"RVN-01 // MESH // MESSAGE FROM {sender_name}")
        try:
            self.ops_engine.record_event(
                self.operations.active.id, "MESH-RX", f"{sender_name}: {text}", metadata={"sender_id": sender_id}
            )
        except Exception:
            pass

    def _send_mesh_message(self) -> None:
        text = self.mesh_message_input.text().strip()
        if not text:
            return
        if self.mesh_interface is None:
            self.footer.setText("RVN-01 // MESH // NOT CONNECTED // PRESS CONNECT FIRST")
            return
        try:
            self.mesh_interface.sendText(text)
        except Exception as exc:
            self.footer.setText(f"RVN-01 // MESH // SEND FAILED // {type(exc).__name__}")
            return
        stamp = datetime.now().strftime("%H:%M:%S")
        self.mesh_messages_list.addItem(f"[{stamp}] YOU: {text}")
        self.mesh_message_input.clear()
        self.footer.setText("RVN-01 // MESH // MESSAGE SENT")
        try:
            self.ops_engine.record_event(self.operations.active.id, "MESH-TX", text, metadata={})
        except Exception:
            pass

    def closeEvent(self, event) -> None:
        if self.mesh_interface is not None:
            try:
                self.mesh_interface.close()
            except Exception:
                pass
        super().closeEvent(event)

    def _collect_futures(self) -> None:
        mesh_nodes_future = self.futures.get("MESHNODES")
        mesh_nodes_value = None
        if mesh_nodes_future is not None and mesh_nodes_future.done():
            try:
                mesh_nodes_value = mesh_nodes_future.result()
            except Exception:
                mesh_nodes_value = ()

        mesh_connect_future = self.futures.get("MESHCONNECT")
        mesh_connect_done = mesh_connect_future is not None and mesh_connect_future.done()
        mesh_connect_result = None
        if mesh_connect_done:
            try:
                mesh_connect_result = mesh_connect_future.result()
            except Exception:
                mesh_connect_result = None

        wifi_scan_future = self.futures.get("WIFISCAN")
        wifi_scan_value = None
        if wifi_scan_future is not None and wifi_scan_future.done():
            try:
                wifi_scan_value = wifi_scan_future.result()
            except Exception:
                wifi_scan_value = ()

        super()._collect_futures()

        if wifi_scan_value is not None:
            self.wifi_scan_button.setEnabled(True)
            self.network_wifi_list.clear()
            if wifi_scan_value:
                for net in wifi_scan_value:
                    signal = f"{net.signal}%" if net.signal is not None else "--"
                    channel = str(net.channel) if net.channel is not None else "--"
                    self.network_wifi_list.addItem(f"{net.ssid:<20} CH{channel:<4} {signal:<5} {net.security}")
                self.footer.setText(f"RVN-01 // NETWORK // WI-FI SCAN // {len(wifi_scan_value)} NETWORK(S)")
            else:
                self.network_wifi_list.addItem("NO NETWORKS FOUND")
                self.footer.setText("RVN-01 // NETWORK // WI-FI SCAN // NO NETWORKS FOUND")

        if mesh_nodes_value is not None:
            self.mesh_nodes_list.clear()
            if mesh_nodes_value:
                for node in mesh_nodes_value:
                    last_heard = node.last_heard or "--"
                    self.mesh_nodes_list.addItem(f"{node.name:<20} {node.id:<12} LAST {last_heard}")
            else:
                self.mesh_nodes_list.addItem("NO NODES REPORTED")

        if mesh_connect_done:
            self.mesh_connect_button.setEnabled(True)
            if mesh_connect_result is not None:
                self.mesh_interface = mesh_connect_result
                try:
                    from pubsub import pub
                    pub.subscribe(self._mesh_pubsub_callback, "meshtastic.receive")
                except Exception:
                    pass
                self.mesh_connect_button.setText("DISCONNECT")
                self._refresh_mesh_from_persistent()
                self.footer.setText("RVN-01 // MESH // CONNECTED")
            else:
                self.mesh_status.setText("LINK        CONNECT FAILED // NO DEVICE")
                self.footer.setText("RVN-01 // MESH // CONNECT FAILED")

    def _navigation_page(self) -> QWidget:
        page, layout = self._shell("NAVIGATION", "Offline map // live GNSS overlay")
        self.map_canvas = MapCanvas()
        layout.addWidget(self.map_canvas, 2)
        self.map_status = QLabel("GPS         PROBING")
        self.map_status.setObjectName("body")
        layout.addWidget(self.map_status)

        row = QHBoxLayout()
        refresh = QPushButton("REFRESH GPS")
        refresh.clicked.connect(lambda: self.refresh_module("MAP"))
        row.addWidget(refresh)
        companion = QPushButton("OPEN QMAPSHACK")
        companion.clicked.connect(lambda: self.launch_first_service("MAP"))
        row.addWidget(companion)
        layout.addLayout(row)

        self._back(layout)
        return page

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
        for i, (name, kind, desc) in enumerate(FIELD_APPS):
            button = build_tile_button(name, kind, desc)
            button.clicked.connect(lambda checked=False, n=name: self.open_app(n)); grid.addWidget(button, i // 3, i % 3); self.buttons.append(button)
        layout.addLayout(grid)
        layout.addStretch(1)
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
        if name == "NAVIGATION": self.refresh_module("MAP")
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
    app = QApplication.instance() or QApplication(sys.argv); load_bundled_fonts(); app.setStyleSheet(V29_STYLE)
    window = FieldOSWindow(); window.show() if "--windowed" in sys.argv else window.showFullScreen()
    print("FIELD//OS: V2.9 graphical field-computer window created", flush=True)
    return app.exec()


if __name__ == "__main__": raise SystemExit(main())
