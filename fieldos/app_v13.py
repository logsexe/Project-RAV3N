from __future__ import annotations

from datetime import datetime

from rich.text import Text
from textual.binding import Binding
from textual.widgets import Input, Static

from .app_v12 import FieldOSApp as V12FieldOSApp, NAV_ITEMS, OperatorPane


MENU_ICONS = {
    "DASHBOARD": "◉",
    "TOOLS": "◆",
    "PLAYBOOKS": "▶",
    "OPERATIONS": "▣",
    "ASSETS": "◎",
    "EVIDENCE": "▤",
    "INTEL": "⌁",
    "KNOWLEDGE": "≡",
    "TERMINAL": ">_",
    "HARDWARE": "⚙",
    "SETTINGS": "◇",
}


class FieldOSApp(V12FieldOSApp):
    """FIELD//OS V1.3 — Flipper-inspired 800x480 RAVEN operator interface."""

    TITLE = "RAVEN // FIELD//OS V1.3"

    # Arrow keys intentionally behave like a D-pad. Enter is the centre/OK button,
    # Escape is Back. Enter is not priority-bound so terminal Input can submit.
    BINDINGS = [
        Binding("up", "move_up", show=False, priority=True),
        Binding("down", "move_down", show=False, priority=True),
        Binding("left", "move_left", show=False, priority=True),
        Binding("right", "move_right", show=False, priority=True),
        Binding("enter", "open", show=False),
        Binding("escape", "back", show=False, priority=True),
        Binding("/", "search", show=False),
        Binding("f1", "help", "Help"), Binding("f2", "terminal", "Terminal"),
        Binding("f3", "sessions", "Operations"), Binding("f4", "status", "Hardware"),
        Binding("f5", "notes", "Notes"), Binding("f9", "playbooks", "Playbooks"),
        Binding("f10", "theme", "Theme"), Binding("f11", "profile", "Profile"),
        Binding("f12", "intelligence", "Intel"),
        Binding("ctrl+c", "interrupt", "Interrupt", show=False),
        Binding("ctrl+q", "quit", "Quit"),
    ]

    CSS = """
    Screen { background: #f58a13; color: #1a0b00; }
    #shell { height: 1fr; padding: 0 1; background: #f58a13; }
    #status { height: 1; color: #1a0b00; background: #ff9e2e; text-style: bold; }
    #breadcrumb { height: 1; color: #3a1600; background: #f58a13; }
    #title { height: 1; color: #140700; background: #f58a13; text-style: bold; }
    #description { height: 1; color: #4a1c00; background: #f58a13; }
    #body { height: 1fr; padding: 1 2; border: solid #1a0b00; background: #f58a13; color: #1a0b00; }
    #body:focus { border: heavy #1a0b00; background: #f58a13; }
    #example { height: 1; color: #3a1600; background: #f58a13; padding: 0 1; }
    #search, #entry, #command { height: 3; border: tall #1a0b00; background: #ff9e2e; color: #1a0b00; }
    #search:focus, #entry:focus, #command:focus { border: heavy #1a0b00; }
    #terminal-tabs { height: 1; color: #1a0b00; background: #ff9e2e; text-style: bold; }
    #terminal-output { height: 1fr; padding: 0 1; border: solid #1a0b00; background: #f58a13; color: #1a0b00; }
    #footer { height: 1; color: #f58a13; background: #1a0b00; text-align: center; text-style: bold; }
    .hidden { display: none; }
    """

    def __init__(self) -> None:
        super().__init__()
        self.nav_index = 0
        self.settings_index = 0

    def refresh_status(self) -> None:
        t = self.telemetry_provider.read()
        airgap = self._airgap_state()
        clock = datetime.now().strftime("%H:%M")
        temp = "--" if t.cpu_temp_c < 0 else f"{t.cpu_temp_c:.0f}C"
        net = "OFF" if airgap.active else self._telemetry_flag(t.network)
        self.query_one("#status", Static).update(
            f" RVN-01   {clock}   NET:{net}   GPS:{self._telemetry_flag(t.gps)}   "
            f"MESH:{self._telemetry_flag(t.mesh)}   CPU:{temp}   {self.profiles.current.name} "
        )

    def _footer(self, left: str, centre: str, right: str) -> str:
        return f" {left:<20} {centre:^26} {right:>20} "

    def render_home(self) -> None:
        """Flipper-like desktop: status + identity + four directional shortcuts."""
        self.view = "home"
        self.hide_aux()
        t = self.telemetry_provider.read()
        airgap = self._airgap_state()
        op = self.operations.active.id
        assets = len(self.intelligence.list_assets(op))
        evidence = len(self.intelligence.list_evidence(op))
        events = len(self.intelligence.timeline(op, limit=999))

        body = Text()
        body.append("\n                 R A V E N\n", style="bold")
        body.append("              FIELD OPERATIONS\n\n")
        body.append("                    ▲\n")
        body.append("                 SETTINGS\n\n")
        body.append("       ◀ PLAYBOOKS     OK MENU      TERMINAL ▶\n\n")
        body.append("                 HARDWARE\n")
        body.append("                    ▼\n\n")
        body.append(f" OP {op:<14}  A:{assets:03d} E:{evidence:03d} T:{events:03d}\n")
        body.append(
            f" LINK {'AIRGAP' if airgap.active else 'ONLINE':<7}   NET {self._telemetry_flag(t.network)}   "
            f"GPS {self._telemetry_flag(t.gps)}   MESH {self._telemetry_flag(t.mesh)}"
        )
        self.query_one("#body", OperatorPane).update(body)
        self.set_header(
            "RAVEN / DESKTOP",
            "RVN-01",
            f"{self.operations.active.name} // {self.profiles.current.name}",
            self._footer("ESC BACK", "ENTER MENU", "ARROWS QUICK ACCESS"),
        )
        self.focus_body()

    def render_main_menu(self) -> None:
        self.view = "main-menu"
        self.hide_aux()
        text = Text()
        text.append("MAIN MENU\n\n", style="bold")
        start = max(0, min(self.nav_index - 4, len(NAV_ITEMS) - 8))
        end = min(len(NAV_ITEMS), start + 8)
        for i in range(start, end):
            name, desc = NAV_ITEMS[i]
            icon = MENU_ICONS.get(name, "•")
            row = f" {icon:<2} {name:<13} {desc[:36]} "
            if i == self.nav_index:
                text.append(row + "\n", style="reverse bold")
            else:
                text.append(row + "\n")
        text.append(f"\n                 {self.nav_index + 1:02d}/{len(NAV_ITEMS):02d}")
        self.query_one("#body", OperatorPane).update(text)
        self.set_header(
            "RAVEN / MENU",
            "APPLICATIONS",
            "UP/DOWN TO SELECT // ENTER TO OPEN",
            self._footer("ESC DESKTOP", "ENTER OPEN", "LEFT BACK"),
        )
        self.focus_body()

    def _open_menu_choice(self) -> None:
        choice = NAV_ITEMS[self.nav_index][0]
        if choice == "DASHBOARD": self.render_home()
        elif choice == "TOOLS": self.render_tools_home()
        elif choice == "PLAYBOOKS": self.action_playbooks()
        elif choice == "OPERATIONS": self.action_sessions()
        elif choice == "ASSETS": self.render_assets()
        elif choice == "EVIDENCE": self.render_evidence()
        elif choice == "INTEL": self.action_intelligence()
        elif choice == "KNOWLEDGE": self.render_knowledge()
        elif choice == "TERMINAL": self.action_terminal()
        elif choice == "HARDWARE": self.action_status()
        elif choice == "SETTINGS": self.render_settings()

    def render_tools_home(self) -> None:
        super().render_tools_home()
        self.set_header("RAVEN / TOOLS", "TOOLS", f"PROFILE {self.profiles.current.name}", self._footer("ESC MENU", "ENTER OPEN", "UP/DN SELECT"))

    def render_library(self) -> None:
        super().render_library()
        self.set_header("RAVEN / TOOLS / LIBRARY", "TOOL LIBRARY", CATEGORIES[self.category_index][0], self._footer("ESC BACK", "ENTER DETAILS", "UP/DN SELECT"))

    def render_tool(self) -> None:
        super().render_tool()
        if not self.active_tools:
            return
        tool = self.active_tools[self.tool_index]
        self.set_header("RAVEN / TOOL", tool.name.upper(), tool.description or "Indexed tool", self._footer("ESC BACK", "ENTER STAGE", "UP/DN RECIPE"))

    def action_playbooks(self) -> None:
        super().action_playbooks()
        self.set_header("RAVEN / PLAYBOOKS", "PLAYBOOKS", "Guided operator workflows", self._footer("ESC MENU", "ENTER OPEN", "UP/DN SELECT"))

    def render_playbook(self) -> None:
        super().render_playbook()
        if not self.playbooks.all:
            return
        p = self.playbooks.all[self.playbook_index]
        self.set_header("RAVEN / PLAYBOOK", p.name.upper(), p.description, self._footer("ESC BACK", "ENTER ACTION", "UP/DN STEP"))

    def render_terminal(self) -> None:
        super().render_terminal()
        session = self.terminals.active
        self.set_header(
            "RAVEN / TERMINAL",
            f"{session.name} // {'RUNNING' if session.running else 'READY'}",
            session.cwd,
            self._footer("ESC MENU", "ENTER EXEC", "UP/DN HISTORY"),
        )

    def render_assets(self) -> None:
        super().render_assets()
        self.set_header("RAVEN / ASSETS", "ASSET REGISTRY", self.operations.active.id, self._footer("ESC MENU", "/ SEARCH", ""))

    def render_evidence(self) -> None:
        super().render_evidence()
        self.set_header("RAVEN / EVIDENCE", "EVIDENCE VAULT", self.operations.active.id, self._footer("ESC MENU", "SHA256 TRACKED", ""))

    def render_settings(self) -> None:
        super().render_settings()
        self.set_header("RAVEN / SETTINGS", "SETTINGS", "Profile / theme / isolation", self._footer("ESC MENU", "ENTER CHANGE", "UP/DN SELECT"))

    def action_move_up(self) -> None:
        if isinstance(self.focused, Input):
            if self.view == "terminal":
                self.history_up()
            return
        if self.view == "home":
            self.render_settings()
        elif self.view == "main-menu":
            self.nav_index = (self.nav_index - 1) % len(NAV_ITEMS)
            self.render_main_menu()
        else:
            super().action_move_up()

    def action_move_down(self) -> None:
        if isinstance(self.focused, Input):
            if self.view == "terminal":
                self.history_down()
            return
        if self.view == "home":
            self.action_status()
        elif self.view == "main-menu":
            self.nav_index = (self.nav_index + 1) % len(NAV_ITEMS)
            self.render_main_menu()
        else:
            super().action_move_down()

    def action_move_left(self) -> None:
        if isinstance(self.focused, Input):
            return
        if self.view == "home":
            self.action_playbooks()
        elif self.view == "main-menu":
            self.render_home()
        else:
            self.action_back()

    def action_move_right(self) -> None:
        if isinstance(self.focused, Input):
            return
        if self.view == "home":
            self.action_terminal()
        elif self.view == "main-menu":
            self._open_menu_choice()
        else:
            self.action_open()

    def action_open(self) -> None:
        if isinstance(self.focused, Input):
            return
        if self.view == "home":
            self.render_main_menu()
            return
        if self.view == "main-menu":
            self._open_menu_choice()
            return
        super().action_open()

    def action_back(self) -> None:
        if isinstance(self.focused, Input):
            super().action_back()
            return
        if self.view == "main-menu":
            self.render_home()
        elif self.view == "tool":
            self.render_library()
        elif self.view == "library":
            self.render_tools_home()
        elif self.view == "playbook":
            self.action_playbooks()
        elif self.view == "knowledge-detail":
            self.render_knowledge()
        elif self.view in {
            "terminal", "intelligence", "status", "sessions", "knowledge", "notes",
            "assets", "evidence", "settings", "playbooks", "tools-home", "help",
            "favourites", "recent", "search"
        }:
            self.render_main_menu()
        else:
            self.render_home()
