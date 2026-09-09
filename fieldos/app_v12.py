from __future__ import annotations

import time

from textual.binding import Binding
from textual.widgets import Input, Static

from fieldos.app_v05 import CATEGORIES, OperatorPane
from fieldos.app_v11 import FieldOSApp as BaseFieldOSApp

NAV_ITEMS = (
    ("DASHBOARD", "Operational overview"),
    ("TOOLS", "Command and recipe library"),
    ("PLAYBOOKS", "Guided field workflows"),
    ("OPERATIONS", "Cases and field sessions"),
    ("ASSETS", "Tracked investigation entities"),
    ("EVIDENCE", "Collected and verified artefacts"),
    ("INTEL", "Timeline and intelligence state"),
    ("KNOWLEDGE", "Offline reference library"),
    ("TERMINAL", "Operator shell sessions"),
    ("HARDWARE", "RVN-01 system telemetry"),
    ("SETTINGS", "Profile and visual controls"),
)


class FieldOSApp(BaseFieldOSApp):
    """FIELD//OS V1.2 keyboard-first hacker themed operator interface."""

    TITLE = "RAVEN // FIELD//OS V1.2"
    CSS = """
    Screen { background: #010402; color: #9cffb3; }
    #shell { height: 1fr; padding: 0 1; }
    #status { height: 1; color: #7dff9b; background: #020a05; text-style: bold; }
    #breadcrumb { height: 1; color: #4f9c62; }
    #title { height: 2; color: #caffd6; text-style: bold; padding-top: 1; }
    #description { height: 2; color: #65a875; }
    #body { height: 1fr; padding: 1 2; border: solid #1f5d31; background: #020705; }
    #body:focus { border: heavy #63ff88; background: #041009; }
    #example { height: 2; color: #65a875; padding: 0 1; }
    #search, #entry, #command { height: 3; border: tall #2d6b3d; background: #010704; color: #bfffcf; }
    #search:focus, #entry:focus, #command:focus { border: tall #7dff9b; }
    #terminal-tabs { height: 1; color: #7dff9b; text-style: bold; }
    #terminal-output { height: 1fr; padding: 0 1; border: solid #1f5d31; background: #000201; color: #9cffb3; }
    #footer { height: 1; color: #65a875; background: #020a05; text-align: center; }
    .hidden { display: none; }
    """

    # ESC remains priority so no screen can swallow the back action. Enter/Left/Right
    # are deliberately non-priority so Textual Input widgets can submit and edit normally.
    BINDINGS = [
        Binding("up", "move_up", show=False, priority=True),
        Binding("down", "move_down", show=False, priority=True),
        Binding("right", "open", show=False),
        Binding("enter", "open", show=False),
        Binding("left", "back", show=False),
        Binding("escape", "back", show=False, priority=True),
        Binding("/", "search", show=False),
        Binding("f1", "help", "Help"),
        Binding("f2", "terminal", "Terminal"),
        Binding("f3", "sessions", "Operations"),
        Binding("f4", "status", "Hardware"),
        Binding("f5", "notes", "Notes"),
        Binding("f9", "playbooks", "Playbooks"),
        Binding("f10", "theme", "Theme"),
        Binding("f11", "profile", "Profile"),
        Binding("f12", "intelligence", "Intel"),
        Binding("ctrl+c", "interrupt", "Interrupt", show=False),
        Binding("ctrl+q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.nav_index = 0
        self.settings_index = 0
        self._airgap_cache = None
        self._airgap_checked_at = 0.0

    def _airgap_state(self):
        now = time.monotonic()
        if self._airgap_cache is None or now - self._airgap_checked_at >= 5.0:
            self._airgap_cache = self.airgap.status()
            self._airgap_checked_at = now
        return self._airgap_cache

    def refresh_status(self) -> None:
        t = self.telemetry_provider.read()
        a = self._airgap_state()
        battery = "EXT" if t.battery_percent < 0 else f"{t.battery_percent}%"
        self.query_one("#status", Static).update(
            f"[ RVN-01 ] FIELD//OS V1.2  ::  {self.operations.active.id:<12}  ::  "
            f"{self.profiles.current.name:<9}  ::  {'AIRGAP' if a.active else 'ONLINE':<7}  ::  BAT {battery}"
        )

    @staticmethod
    def _telemetry_flag(value: object) -> str:
        return "--" if str(value).upper() in {"OFF", "NOT PRESENT", "DISCONNECTED", "UNKNOWN", "NO FIX"} else "OK"

    def render_home(self) -> None:
        self.view = "home"
        self.hide_aux()
        t = self.telemetry_provider.read()
        a = self._airgap_state()
        op = self.operations.active.id
        assets = len(self.intelligence.list_assets(op))
        evidence = len(self.intelligence.list_evidence(op))
        events = len(self.intelligence.timeline(op, limit=999))
        temp = "--" if t.cpu_temp_c < 0 else f"{t.cpu_temp_c:.1f}C"

        nav = [f"{'>_' if i == self.nav_index else '  '} {name:<12}" for i, (name, _) in enumerate(NAV_ITEMS)]
        stat = [
            ":: ACTIVE NODE ::",
            f"OP      {op}",
            f"PROFILE {self.profiles.current.name}",
            "",
            f"ASSET   {assets:03d}",
            f"EVID    {evidence:03d}",
            f"EVENT   {events:03d}",
            "",
            f"NET     {self._telemetry_flag(t.network)}",
            f"GPS     {self._telemetry_flag(t.gps)}",
            f"MESH    {self._telemetry_flag(t.mesh)}",
            f"CPU     {temp}",
            f"ISO     {'ON' if a.active else 'OFF'}",
        ]

        lines = [
            "┌─ RAVEN / FIELD OPERATIONS TERMINAL ───────────────────────────────┐",
            "│ OPERATOR MATRIX                    NODE TELEMETRY                 │",
            "├───────────────────────────────────┬──────────────────────────────┤",
        ]
        rows = max(len(nav), len(stat))
        for i in range(rows):
            left = nav[i] if i < len(nav) else ""
            right = stat[i] if i < len(stat) else ""
            lines.append(f"│ {left:<33}│ {right:<28}│")
        lines.append("└───────────────────────────────────┴──────────────────────────────┘")

        self.query_one("#body", OperatorPane).update("\n".join(lines))
        self.set_header(
            "ROOT://FIELDOS/DASHBOARD",
            "RAVEN // ACCESS GRANTED",
            f"NODE RVN-01 // {self.operations.active.name} // PROFILE {self.profiles.current.name}",
            "↑↓ MOVE  ENTER EXECUTE  / SEARCH  ESC RETURN  CTRL+Q DISCONNECT",
        )
        self.focus_body()

    def render_tools_home(self) -> None:
        self.view = "tools-home"
        self.hide_aux()
        lines = [":: TOOL INDEX ::", ""]
        for i, (name, desc) in enumerate(CATEGORIES):
            count = len(self.profiles.filter_tools(self.tools.for_category(name.lower())))
            lines.append(f"{'>_' if i == self.category_index else '  '} {name:<12} [{count:02d}]  {desc}")
        self.query_one("#body", OperatorPane).update("\n".join(lines))
        self.set_header("ROOT://FIELDOS/TOOLS", "ARSENAL INDEX", f"PROFILE FILTER // {self.profiles.current.name}", "ESC RETURN  ↑↓ SELECT  ENTER OPEN  / SEARCH")
        self.focus_body()

    def render_library(self) -> None:
        self.view = "library"
        self.hide_aux()
        category, desc = CATEGORIES[self.category_index]
        self.active_tools = list(self.profiles.filter_tools(self.tools.for_category(category.lower())))
        self.tool_index = min(self.tool_index, max(0, len(self.active_tools) - 1))
        lines = [f":: {category} MODULES ::", ""]
        for i, tool in enumerate(self.active_tools):
            marker = ">_" if i == self.tool_index else "  "
            fav = "*" if self.state.is_favourite(tool.id) else " "
            state = "READY" if tool.installed else "OFFLN"
            lines.append(f"{marker} {fav} {tool.name[:24]:<24} [{state}] {(tool.subcategory or 'general').upper()[:22]}")
        self.query_one("#body", OperatorPane).update("\n".join(lines) if self.active_tools else "NO MODULES AVAILABLE IN CURRENT PROFILE")
        self.set_header(f"ROOT://FIELDOS/TOOLS/{category}", f"{category} // MODULE LIBRARY", desc, "ESC RETURN  ↑↓ SELECT  ENTER INSPECT  / SEARCH")
        self.focus_body()

    def render_tool(self) -> None:
        if not self.active_tools:
            return
        self.view = "tool"
        self.hide_aux()
        tool = self.active_tools[self.tool_index]
        self.state.record_recent(tool.id)
        recipe = tool.recipes[self.recipe_index] if tool.recipes else None
        lines = [
            "┌─ MODULE DOSSIER ────────────────────────────────────────────────",
            f"│ NAME      {tool.name}",
            f"│ CLASS     {tool.category.upper()} / {(tool.subcategory or 'GENERAL').upper()}",
            f"│ STATE     {'READY' if tool.installed else 'NOT INSTALLED'}",
            f"│ PRIORITY  {tool.priority.upper()}",
            f"│ ACCESS    {'AUTHORISED USE' if tool.authorised_use_only else 'STANDARD'}",
            "├─ DESCRIPTION",
            f"│ {tool.description or 'FIELD//OS indexed tool'}",
            "├─ RECIPES",
        ]
        if tool.recipes:
            for i, item in enumerate(tool.recipes):
                lines.append(f"│ {'>_' if i == self.recipe_index else '  '} {item.name}")
            lines.extend(["├─ STAGED COMMAND", f"│ $ {recipe.command}"])
        elif tool.command:
            lines.extend(["│ >_ BASE COMMAND", "├─ STAGED COMMAND", f"│ $ {tool.command}"])
        else:
            lines.append("│ NO COMMAND RECIPE INDEXED")
        lines.append("└─────────────────────────────────────────────────────────────────")
        self.query_one("#body", OperatorPane).update("\n".join(lines))
        self.set_header(f"ROOT://FIELDOS/{tool.category.upper()}/{tool.name.upper()}", tool.name.upper(), "Review before execution // capture enabled", "ESC RETURN  ↑↓ RECIPE  ENTER STAGE  F FAV  F2 SHELL")
        self.focus_body()

    def render_assets(self) -> None:
        self.view = "assets"
        self.hide_aux()
        items = self.intelligence.list_assets(self.operations.active.id)
        lines = [":: ASSET REGISTRY ::", "ID           TYPE         SELECTOR", "------------ ------------ ------------------------------------------"]
        lines.extend(f"{item.id:<12} {item.kind[:12]:<12} {item.value}" for item in items[:18])
        if not items:
            lines.append("NO ASSETS RECORDED")
        self.query_one("#body", OperatorPane).update("\n".join(lines))
        self.set_header("ROOT://FIELDOS/ASSETS", "ASSET REGISTRY", f"{len(items)} tracked selectors // {self.operations.active.id}", "ESC RETURN  / SEARCH")
        self.focus_body()

    def render_evidence(self) -> None:
        self.view = "evidence"
        self.hide_aux()
        items = self.intelligence.list_evidence(self.operations.active.id)
        lines = [":: EVIDENCE VAULT ::", "ID           SHA256       MODE  SOURCE", "------------ ------------ ----- ------------------------------------"]
        lines.extend(f"{item.id:<12} {item.sha256[:12]} {'ENC' if item.encrypted else 'RAW':<5} {item.source_name}" for item in items[:18])
        if not items:
            lines.append("NO EVIDENCE RECORDED")
        self.query_one("#body", OperatorPane).update("\n".join(lines))
        self.set_header("ROOT://FIELDOS/EVIDENCE", "EVIDENCE VAULT", f"{len(items)} artefacts // SHA256 indexed", "ESC RETURN")
        self.focus_body()

    def render_settings(self) -> None:
        self.view = "settings"
        self.hide_aux()
        a = self._airgap_state()
        rows = [
            ("PROFILE", self.profiles.current.name, "cycle operational profile"),
            ("THEME", self.themes.current.name, "cycle terminal palette"),
            ("AIRGAP", "ACTIVE" if a.active else "OFF", "manual isolation control"),
        ]
        lines = [":: SYSTEM CONTROL ::", ""]
        for i, (name, value, desc) in enumerate(rows):
            lines.append(f"{'>_' if i == self.settings_index else '  '} {name:<10} {value:<18} // {desc}")
        self.query_one("#body", OperatorPane).update("\n".join(lines))
        self.set_header("ROOT://FIELDOS/CONFIG", "SYSTEM CONTROL", "Local operator configuration", "ESC RETURN  ↑↓ SELECT  ENTER CHANGE")
        self.focus_body()

    def render_terminal(self) -> None:
        super().render_terminal()
        session = self.terminals.active
        self.set_header(
            f"ROOT://FIELDOS/{self.operations.active.id}/SHELL",
            f"SHELL::{session.name} // {'BUSY' if session.running else 'READY'}",
            f"CWD // {session.cwd}",
            "ENTER RUN  ↑↓ HISTORY  TAB NEXT  SHIFT+TAB PREV  F6 NEW  F7 CLOSE  F8 CLEAR  ESC RETURN",
        )

    def action_move_up(self) -> None:
        if self.view == "home":
            self.nav_index = max(0, self.nav_index - 1); self.render_home()
        elif self.view == "tools-home":
            self.category_index = max(0, self.category_index - 1); self.render_tools_home()
        elif self.view == "settings":
            self.settings_index = max(0, self.settings_index - 1); self.render_settings()
        else:
            super().action_move_up()

    def action_move_down(self) -> None:
        if self.view == "home":
            self.nav_index = min(len(NAV_ITEMS) - 1, self.nav_index + 1); self.render_home()
        elif self.view == "tools-home":
            self.category_index = min(len(CATEGORIES) - 1, self.category_index + 1); self.render_tools_home()
        elif self.view == "settings":
            self.settings_index = min(2, self.settings_index + 1); self.render_settings()
        else:
            super().action_move_down()

    def action_open(self) -> None:
        # Inputs own Enter so command submission/search entry work normally.
        if isinstance(self.focused, Input):
            return
        if self.view == "home":
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
            return
        if self.view == "tools-home":
            self.tool_index = 0; self.recipe_index = 0; self.render_library(); return
        if self.view == "settings":
            if self.settings_index == 0:
                self.action_profile(); self.render_settings()
            elif self.settings_index == 1:
                self.action_theme(); self.render_settings()
            return
        super().action_open()

    def action_back(self) -> None:
        if isinstance(self.focused, Input):
            # ESC is priority and intentionally exits input-driven views/terminal.
            if self.view == "terminal":
                self.render_home()
            else:
                super().action_back()
            return
        if self.view == "library": self.render_tools_home()
        elif self.view == "tools-home": self.render_home()
        elif self.view in {"assets", "evidence", "settings", "playbooks", "intelligence", "status", "sessions", "knowledge", "notes", "terminal"}: self.render_home()
        elif self.view == "playbook": self.action_playbooks()
        elif self.view == "tool": self.render_library()
        else: super().action_back()

    def open_tool(self, tool) -> None:
        for i, (name, _) in enumerate(CATEGORIES):
            if name.lower() == tool.category.lower():
                self.category_index = i
                break
        self.active_tools = list(self.profiles.filter_tools(self.tools.for_category(tool.category)))
        self.tool_index = next((i for i, item in enumerate(self.active_tools) if item.id == tool.id), 0)
        self.recipe_index = 0
        self.render_tool()

    def render_search_results(self, query: str) -> None:
        tool_matches = [t for t in self.tools.search(query) if self.profiles.allows_tool(t)]
        knowledge_matches = self.knowledge.search(query)
        q = query.lower()
        asset_matches = [x for x in self.intelligence.list_assets(self.operations.active.id) if q in x.value.lower() or q in x.kind.lower() or q in (x.label or "").lower()]
        self.search_results = [("tool", x) for x in tool_matches[:16]] + [("knowledge", x) for x in knowledge_matches[:12]] + [("asset", x) for x in asset_matches[:12]]
        self.search_index = min(self.search_index, max(0, len(self.search_results) - 1))
        lines = [":: GLOBAL QUERY RESULTS ::", ""]
        for i, (kind, item) in enumerate(self.search_results):
            marker = ">_" if i == self.search_index else "  "
            if kind == "tool": lines.append(f"{marker} TOOL   {item.name[:28]:<28} {item.category.upper()}")
            elif kind == "knowledge": lines.append(f"{marker} KNOW   {item.title[:28]:<28} {item.category.upper()}")
            else: lines.append(f"{marker} ASSET  {item.value[:28]:<28} {item.kind.upper()}")
        self.query_one("#body", OperatorPane).update("\n".join(lines) if self.search_results else "NO MATCHES")
        self.set_header("ROOT://FIELDOS/SEARCH", f'QUERY // "{query.upper()}"', f"{len(self.search_results)} match(es)", "↑↓ SELECT  ENTER OPEN  ESC RETURN")
        self.focus_body()

    def action_help(self) -> None:
        if self.view != "help":
            self.return_view = self.view
        self.view = "help"
        self.hide_aux()
        self.query_one("#body", OperatorPane).update(
            ":: OPERATOR KEYMAP ::\n\n"
            "↑ ↓        MOVE / SHELL HISTORY\n"
            "ENTER      OPEN / RUN COMMAND\n"
            "ESC        RETURN\n"
            "/          GLOBAL QUERY\n\n"
            "F2         SHELL\nF3         OPERATIONS\nF4         HARDWARE\n"
            "F5         NOTES\nF9         PLAYBOOKS\nF10        THEME\n"
            "F11        PROFILE\nF12        INTELLIGENCE\nCTRL+Q     DISCONNECT FIELD//OS"
        )
        self.set_header("ROOT://FIELDOS/HELP", "OPERATOR KEYMAP", "Keyboard-first controls for RVN-01", "ESC RETURN")
        self.focus_body()
