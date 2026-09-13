from __future__ import annotations

from dataclasses import dataclass

from textual.widgets import Static

from .app_v12 import OperatorPane
from .app_v15_recovery import FieldOSApp as V15FieldOSApp


@dataclass(frozen=True)
class FieldApp:
    id: str
    label: str
    subtitle: str
    status: str


FIELD_APPS = (
    FieldApp("radio", "RADIO", "Wideband receive / spectrum", "HW PENDING"),
    FieldApp("map", "MAP", "Offline navigation / position", "GPS LINK"),
    FieldApp("mesh", "MESH", "Off-grid node communications", "MESHTASTIC"),
    FieldApp("network", "NETWORK", "Local diagnostics / inventory", "READY"),
    FieldApp("intel", "INTEL", "Assets / evidence / timeline", "READY"),
    FieldApp("library", "LIBRARY", "Offline field knowledge", "READY"),
    FieldApp("files", "FILES", "Operation data / local storage", "READY"),
    FieldApp("terminal", "TERMINAL", "Linux operator shell", "READY"),
    FieldApp("system", "SYSTEM", "RVN-01 hardware / readiness", "READY"),
)


class FieldOSApp(V15FieldOSApp):
    """FIELD//OS V1.6 app-oriented field-computer shell for RVN-01."""

    TITLE = "RAVEN // FIELD//OS V1.6"

    def __init__(self) -> None:
        super().__init__()
        self.app_index = 0

    def refresh_status(self) -> None:
        t = self._telemetry_snapshot
        a = self._airgap_state()
        temp = "--" if t.cpu_temp_c < 0 else f"{t.cpu_temp_c:.0f}C"
        self.query_one("#status", Static).update(
            f" RVN-01 | FIELD//OS 1.6 | {self.operations.active.id[:10]:<10} | "
            f"{'ISOLATED' if a.active else 'LINKED':<8} | NET {self._telemetry_flag(t.network):<2} "
            f"GPS {self._telemetry_flag(t.gps):<2} MESH {self._telemetry_flag(t.mesh):<2} | {temp:<4} "
        )

    def render_home(self) -> None:
        """Render an appliance-style app launcher as the primary FIELD//OS surface."""
        self.view = "home"
        self.hide_aux()
        t = self._telemetry_snapshot
        readiness, warnings = self._readiness(t)

        lines = [
            "╔═ RAVEN // FIELD//OS ═══════════════════════════════════════════╗",
            f"║ NODE RVN-01   STATE {readiness:<9}   OP {self.operations.active.id[:16]:<16} ║",
            "╠════════════════════════════════════════════════════════════════╣",
        ]
        for row in range(0, len(FIELD_APPS), 3):
            cards = []
            for index in range(row, min(row + 3, len(FIELD_APPS))):
                app = FIELD_APPS[index]
                marker = ">" if index == self.app_index else " "
                cards.append(f"{marker} {app.label:<10} {app.status[:8]:<8}")
            while len(cards) < 3:
                cards.append(" " * 21)
            lines.append(f"║ {cards[0]:<20}│ {cards[1]:<20}│ {cards[2]:<20}║")
        lines.extend([
            "╠════════════════════════════════════════════════════════════════╣",
            f"║ {FIELD_APPS[self.app_index].subtitle[:62]:<62} ║",
        ])
        advisory = " // ".join(warnings[:2]) if warnings else "CORE SYSTEMS NOMINAL"
        lines.append(f"║ ADVISORY // {advisory[:49]:<49} ║")
        lines.append("╚════════════════════════════════════════════════════════════════╝")

        self.query_one("#body", OperatorPane).update("\n".join(lines))
        self.set_header(
            "RVN-01 // FIELD COMPUTER",
            "APPLICATIONS",
            "Offline-first mission workspace // dedicated subsystem apps",
            "ARROWS SELECT  ENTER OPEN  / SEARCH  F2 TERMINAL  F8 COMMAND  ^Q EXIT",
        )
        self.focus_body()

    def _render_app(self, app_id: str, title: str, description: str, body: list[str]) -> None:
        self.view = f"app-{app_id}"
        self.hide_aux()
        self.query_one("#body", OperatorPane).update("\n".join(body))
        self.set_header(
            f"RVN-01 // {title}",
            title,
            description,
            "ESC APPS  F2 TERMINAL  F8 COMMAND CENTER",
        )
        self.focus_body()

    def render_radio_app(self) -> None:
        self._render_app(
            "radio",
            "RADIO",
            "Receive-only RF workspace // hardware capability gated",
            [
                "┌─ RADIO // RF-01 ───────────────────────────────────────────────┐",
                "│ STATE       HARDWARE PENDING                                 │",
                "│ MODE        RECEIVE ONLY                                     │",
                "│ DEVICE      RTL-SDR NOT YET PROVISIONED                       │",
                "│                                                              │",
                "│ FREQUENCY   ---.--- MHz                                      │",
                "│ DEMOD       --                                               │",
                "│ SIGNAL      --                                               │",
                "│                                                              │",
                "│ [ SPECTRUM ]  [ PRESETS ]  [ RECORDINGS ]  [ DEVICE ]         │",
                "│                                                              │",
                "│ FIELD//OS will expose tuning only when a supported RX device  │",
                "│ is detected. No transmit capability is provided by this app.  │",
                "└────────────────────────────────────────────────────────────────┘",
            ],
        )

    def render_map_app(self) -> None:
        t = self._telemetry_snapshot
        self._render_app(
            "map",
            "MAP",
            "Offline navigation workspace",
            [
                "┌─ MAP // NAV-01 ────────────────────────────────────────────────┐",
                f"│ GPS STATE    {str(t.gps)[:48]:<48}│",
                "│ POSITION     --                                               │",
                "│ HEADING      --                                               │",
                "│ ALTITUDE     --                                               │",
                "│                                                              │",
                "│ [ LOCAL MAP ]  [ WAYPOINTS ]  [ TRACK ]  [ GPS STATUS ]        │",
                "│                                                              │",
                "│ Offline map tiles and waypoint storage are the next integration│",
                "│ layer; this shell does not require an Internet connection.     │",
                "└────────────────────────────────────────────────────────────────┘",
            ],
        )

    def render_mesh_app(self) -> None:
        t = self._telemetry_snapshot
        self._render_app(
            "mesh",
            "MESH",
            "Meshtastic node workspace // operator-controlled messaging",
            [
                "┌─ MESH // RVN-NET ──────────────────────────────────────────────┐",
                f"│ LINK STATE   {str(t.mesh)[:48]:<48}│",
                "│ LOCAL NODE   RVN-01                                           │",
                "│ NODES        --                                               │",
                "│                                                              │",
                "│ [ NODES ]  [ MESSAGES ]  [ POSITION ]  [ TELEMETRY ]           │",
                "│                                                              │",
                "│ Message transmission will require an explicit operator action. │",
                "│ No autonomous radio transmission is enabled.                  │",
                "└────────────────────────────────────────────────────────────────┘",
            ],
        )

    def render_files_app(self) -> None:
        op = self.operations.active
        self._render_app(
            "files",
            "FILES",
            "Local operation storage and captured material",
            [
                ":: OPERATION STORAGE ::",
                "",
                f"ACTIVE OP     {op.id}",
                f"NAME          {op.name}",
                f"DATA ROOT     {self.operations.root}",
                "",
                "Use EVIDENCE for verified artefacts and TERMINAL for shell-level",
                "file operations. A dedicated file browser will attach here later.",
            ],
        )

    def render_network_app(self) -> None:
        t = self._telemetry_snapshot
        self._render_app(
            "network",
            "NETWORK",
            "Local network visibility and authorised diagnostics",
            [
                "┌─ NETWORK // NET-01 ────────────────────────────────────────────┐",
                f"│ LINK        {str(t.network)[:49]:<49}│",
                "│                                                              │",
                "│ WORKFLOWS                                                     │",
                "│  > LOCAL BASELINE       interface / route / neighbour review  │",
                "│    DEVICE DISCOVERY     staged authorised subnet discovery    │",
                "│    HOST INSPECTION      staged selected-host inspection       │",
                "│                                                              │",
                "│ ENTER TOOL CENTER from the command workflow for individual    │",
                "│ diagnostics. Active commands remain staged for operator review.│",
                "└────────────────────────────────────────────────────────────────┘",
            ],
        )

    def open_selected_app(self) -> None:
        app_id = FIELD_APPS[self.app_index].id
        if app_id == "radio":
            self.render_radio_app()
        elif app_id == "map":
            self.render_map_app()
        elif app_id == "mesh":
            self.render_mesh_app()
        elif app_id == "network":
            self.render_network_app()
        elif app_id == "intel":
            self.action_intelligence()
        elif app_id == "library":
            self.render_knowledge()
        elif app_id == "files":
            self.render_files_app()
        elif app_id == "terminal":
            self.action_terminal()
        elif app_id == "system":
            self.action_status()

    def action_move_up(self) -> None:
        if self.view == "home":
            self.app_index = max(0, self.app_index - 3)
            self.render_home()
            return
        super().action_move_up()

    def action_move_down(self) -> None:
        if self.view == "home":
            self.app_index = min(len(FIELD_APPS) - 1, self.app_index + 3)
            self.render_home()
            return
        super().action_move_down()

    def action_open(self) -> None:
        if self.view == "home":
            self.open_selected_app()
            return
        super().action_open()

    def on_key(self, event) -> None:
        if self.view == "home" and event.key in {"left", "right"}:
            if event.key == "left":
                self.app_index = max(0, self.app_index - 1)
            else:
                self.app_index = min(len(FIELD_APPS) - 1, self.app_index + 1)
            self.render_home()
            event.prevent_default()
            event.stop()
            return
        super().on_key(event)

    def action_back(self) -> None:
        if self.view.startswith("app-"):
            self.render_home()
            return
        super().action_back()
