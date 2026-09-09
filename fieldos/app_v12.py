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
    """FIELD//OS V1.2 CyberDeck-inspired 800x480 operator interface."""

    TITLE = "RAVEN // FIELD//OS V1.2"
    CSS = """
    Screen { background: #030607; color: #d7ddd9; }
    #shell { height: 1fr; padding: 0 1; }
    #status { height: 1; color: #d7ddd9; background: #0b1214; text-style: bold; }
    #breadcrumb { height: 1; color: #66787c; }
    #title { height: 2; color: #ffffff; text-style: bold; padding-top: 1; }
    #description { height: 2; color: #839398; }
    #body { height: 1fr; padding: 1 2; border: solid #26393d; background: #060b0d; }
    #body:focus { border: heavy #b7c9c8; background: #091113; }
    #example { height: 2; color: #8b999c; padding: 0 1; }
    #search, #entry, #command { height: 3; border: tall #40575b; background: #071012; }
    #search:focus, #entry:focus, #command:focus { border: tall #d7ddd9; }
    #terminal-tabs { height: 1; color: #d7ddd9; text-style: bold; }
    #terminal-output { height: 1fr; padding: 0 1; border: solid #26393d; background: #010304; }
    #footer { height: 1; color: #a8b9bb; background: #0b1214; text-align: center; }
    .hidden { display: none; }
    """

    BINDINGS = [
        Binding("up", "move_up", show=False), Binding("down", "move_down", show=False),
        Binding("right", "open", show=False), Binding("enter", "open", show=False),
        Binding("left", "back", show=False), Binding("escape", "back", show=False),
        Binding("/", "search", show=False), Binding("f1", "help", "Help"),
        Binding("f2", "terminal", "Terminal"), Binding("f3", "sessions", "Operations"),
        Binding("f4", "status", "Hardware"), Binding("f5", "notes", "Notes"),
        Binding("f9", "playbooks", "Playbooks"), Binding("f10", "theme", "Theme"),
        Binding("f11", "profile", "Profile"), Binding("f12", "intelligence", "Intel"),
        Binding("ctrl+c", "interrupt", "Interrupt", show=False), Binding("ctrl+q", "quit", "Quit"),
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
        profile = self.profiles.current.name
        airgap = self._airgap_state()
        isolation = "AIRGAP" if airgap.active else "ONLINE"
        battery = "EXT" if t.battery_percent < 0 else f"{t.battery_percent}%"
        self.query_one("#status", Static).update(
            f"RAVEN // FIELD//OS V1.2   {self.operations.active.id:<12}   {profile:<9}   {isolation:<7}   BAT {battery}"
        )

    @staticmethod
    def _telemetry_flag(value: object) -> str:
        text = str(value).upper()
        return "--" if text in {"OFF", "NOT PRESENT", "DISCONNECTED", "UNKNOWN", "NO FIX"} else "OK"

    def render_home(self) -> None:
        self.view = "home"
        self.hide_aux()
        t = self.telemetry_provider.read()
        airgap = self._airgap_state()
        operation_id = self.operations.active.id
        assets = len(self.intelligence.list_assets(operation_id))
        evidence = len(self.intelligence.list_evidence(operation_id))
        events = len(self.intelligence.timeline(operation_id, limit=999))
        temp = "--" if t.cpu_temp_c < 0 else f"{t.cpu_temp_c:.1f}C"

        nav = []
        for index, (name, _) in enumerate(NAV_ITEMS):
            nav.append(f"{'> ' if index == self.nav_index else '  '}{name:<12}")

        status = [
            "CURRENT OPERATION",
            f"{operation_id}",
            "",
            f"ASSETS      {assets:>3}",
            f"EVIDENCE    {evidence:>3}",
            f"EVENTS      {events:>3}",
            "",
            f"NETWORK     {self._telemetry_flag(t.network):>3}",
            f"GPS         {self._telemetry_flag(t.gps):>3}",
            f"MESH        {self._telemetry_flag(t.mesh):>3}",
            f"CPU         {temp:>7}",
            f"ISOLATION   {'ON' if airgap.active else 'OFF':>3}",
        ]
        rows = max(len(nav), len(status))
        lines = ["OPERATOR MENU                     RVN-01 STATUS", "--------------------------------  ----------------------"]
        for index in range(rows):
            left = nav[index] if index < len(nav) else ""
            right = status[index] if index < len(status) else ""
            lines.append(f"{left:<34}{right}")

        self.query_one("#body", OperatorPane).update("\n".join(lines))
        self.set_header(
            "FIELD//OS > DASHBOARD",
            "RAVEN // FIELD OPERATIONS TERMINAL",
            f"PROFILE {self.profiles.current.name} // {self.operations.active.name}",
            "↑↓ SELECT  ENTER OPEN  / SEARCH  ESC BACK  CTRL+Q EXIT",
        )
        self.focus_body()

    def render_tools_home(self) -> None:
        self.view = "tools-home"
        self.hide_aux()
        lines = []
        for index, (name, desc) in enumerate(CATEGORIES):
            tools = self.profiles.filter_tools(self.tools.for_category(name.lower()))
            marker = ">" if index == self.category_index else " "
            lines.append(f"{marker} {name:<12} {desc:<34} {len(tools):02d}")
        self.query_one("#body", OperatorPane).update("\n".join(lines))
        self.set_header(
            "FIELD//OS > TOOLS",
            "COMMAND // RECIPE LIBRARY",
            f"PROFILE FILTER // {self.profiles.current.name}",
            "ESC BACK  ↑↓ CATEGORY  ENTER OPEN  / SEARCH",
        )
        self.focus_body()

    def render_library(self) -> None:
        self.view = "library"
        self.hide_aux()
        category, desc = CATEGORIES[self.category_index]
        self.active_tools = list(self.profiles.filter_tools(self.tools.for_category(category.lower())))
        self.tool_index = min(self.tool_index, max(0, len(self.active_tools) - 1))
        lines = []
        for index, tool in enumerate(self.active_tools):
            marker = ">" if index == self.tool_index else " "
            fav = "*" if self.state.is_favourite(tool.id) else " "
            state = "READY" if tool.installed else "----"
            lines.append(f"{marker}{fav} {tool.name[:25]:<25} {state:<5} {(tool.subcategory or 'general').upper()[:24]}")
        self.query_one("#body", OperatorPane).update("\n".join(lines) if lines else "NO TOOLS AVAILABLE IN CURRENT PROFILE")
        self.set_header(
            f"FIELD//OS > TOOLS > {category}",
            f"{category} // LIBRARY",
            desc,
            "ESC BACK  ↑↓ SELECT  ENTER DETAILS  / SEARCH",
        )
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
            f"TOOL         {tool.name}",
            f"CATEGORY     {tool.category.upper()} / {(tool.subcategory or 'GENERAL').upper()}",
            f"STATUS       {'INSTALLED' if tool.installed else 'NOT INSTALLED'}",
            f"PRIORITY     {tool.priority.upper()}",
            f"MODE         {'AUTHORISED USE' if tool.authorised_use_only else 'STANDARD'}",
            "",
            "DESCRIPTION",
            tool.description or "FIELD//OS indexed tool",
            "",
            "RECIPES",
        ]
        if tool.recipes:
            for index, item in enumerate(tool.recipes):
                lines.append(f"{'> ' if index == self.recipe_index else '  '}{item.name}")
            lines.extend(["", "STAGED COMMAND", f"$ {recipe.command}"])
        elif tool.command:
            lines.extend(["> BASE COMMAND", "", "STAGED COMMAND", f"$ {tool.command}"])
        else:
            lines.append("NO COMMAND RECIPE INDEXED")
        self.query_one("#body", OperatorPane).update("\n".join(lines))
        self.set_header(
            f"FIELD//OS > {tool.category.upper()} > {tool.name.upper()}",
            tool.name.upper(),
            "Review command before execution; operation capture remains enabled",
            "ESC BACK  ↑↓ RECIPE  ENTER STAGE  F FAVOURITE  F2 TERMINAL",
        )
        self.focus_body()

    def render_assets(self) -> None:
        self.view = "assets"
        self.hide_aux()
        items = self.intelligence.list_assets(self.operations.active.id)
        lines = ["ID           TYPE         VALUE", "------------ ------------ ------------------------------------------"]
        lines.extend(f"{item.id:<12} {item.kind[:12]:<12} {item.value}" for item in items[:18])
        if not items:
            lines.append("NO ASSETS RECORDED FOR THIS OPERATION")
        self.query_one("#body", OperatorPane).update("\n".join(lines))
        self.set_header("FIELD//OS > ASSETS", "ASSET ENGINE", f"{len(items)} tracked entities // {self.operations.active.id}", "ESC BACK  / SEARCH  fieldos-control asset add ...")
        self.focus_body()

    def render_evidence(self) -> None:
        self.view = "evidence"
        self.hide_aux()
        items = self.intelligence.list_evidence(self.operations.active.id)
        lines = ["ID           SHA256       MODE  SOURCE", "------------ ------------ ----- ------------------------------------"]
        lines.extend(f"{item.id:<12} {item.sha256[:12]} {'ENC' if item.encrypted else 'RAW':<5} {item.source_name}" for item in items[:18])
        if not items:
            lines.append("NO EVIDENCE RECORDED FOR THIS OPERATION")
        self.query_one("#body", OperatorPane).update("\n".join(lines))
        self.set_header("FIELD//OS > EVIDENCE", "EVIDENCE ENGINE", f"{len(items)} artefacts // SHA256 tracked", "ESC BACK  fieldos-control evidence ingest ...")
        self.focus_body()

    def render_settings(self) -> None:
        self.view = "settings"
        self.hide_aux()
        airgap = self._airgap_state()
        rows = [
            ("PROFILE", self.profiles.current.name, "ENTER cycles operational profile"),
            ("THEME", self.themes.current.name, "ENTER cycles low-light theme"),
            ("AIRGAP", "ACTIVE" if airgap.active else "OFF", "Use fieldos-control airgap on --confirm"),
        ]
        lines = []
        for index, (name, value, description) in enumerate(rows):
            marker = ">" if index == self.settings_index else " "
            lines.append(f"{marker} {name:<10} {value:<18} {description}")
        self.query_one("#body", OperatorPane).update("\n".join(lines))
        self.set_header("FIELD//OS > SETTINGS", "OPERATOR SETTINGS", "Local profile, appearance and isolation state", "ESC BACK  ↑↓ SELECT  ENTER CHANGE")
        self.focus_body()

    def action_move_up(self) -> None:
        if self.view == "home":
            self.nav_index = max(0, self.nav_index - 1)
            self.render_home()
        elif self.view == "tools-home":
            self.category_index = max(0, self.category_index - 1)
            self.render_tools_home()
        elif self.view == "settings":
            self.settings_index = max(0, self.settings_index - 1)
            self.render_settings()
        else:
            super().action_move_up()

    def action_move_down(self) -> None:
        if self.view == "home":
            self.nav_index = min(len(NAV_ITEMS) - 1, self.nav_index + 1)
            self.render_home()
        elif self.view == "tools-home":
            self.category_index = min(len(CATEGORIES) - 1, self.category_index + 1)
            self.render_tools_home()
        elif self.view == "settings":
            self.settings_index = min(2, self.settings_index + 1)
            self.render_settings()
        else:
            super().action_move_down()

    def action_open(self) -> None:
        if isinstance(self.focused, Input):
            return
        if self.view == "home":
            choice = NAV_ITEMS[self.nav_index][0]
            if choice == "DASHBOARD":
                self.render_home()
            elif choice == "TOOLS":
                self.render_tools_home()
            elif choice == "PLAYBOOKS":
                self.action_playbooks()
            elif choice == "OPERATIONS":
                self.action_sessions()
            elif choice == "ASSETS":
                self.render_assets()
            elif choice == "EVIDENCE":
                self.render_evidence()
            elif choice == "INTEL":
                self.action_intelligence()
            elif choice == "KNOWLEDGE":
                self.render_knowledge()
            elif choice == "TERMINAL":
                self.action_terminal()
            elif choice == "HARDWARE":
                self.action_status()
            elif choice == "SETTINGS":
                self.render_settings()
            return
        if self.view == "tools-home":
            self.tool_index = 0
            self.recipe_index = 0
            self.render_library()
            return
        if self.view == "settings":
            if self.settings_index == 0:
                self.action_profile()
                self.render_settings()
            elif self.settings_index == 1:
                self.action_theme()
                self.render_settings()
            return
        super().action_open()

    def action_back(self) -> None:
        if isinstance(self.focused, Input):
            super().action_back()
            return
        if self.view == "library":
            self.render_tools_home()
        elif self.view == "tools-home":
            self.render_home()
        elif self.view in {"assets", "evidence", "settings"}:
            self.render_home()
        else:
            super().action_back()

    def open_tool(self, tool) -> None:
        for index, (name, _) in enumerate(CATEGORIES):
            if name.lower() == tool.category.lower():
                self.category_index = index
                break
        self.active_tools = list(self.profiles.filter_tools(self.tools.for_category(tool.category)))
        self.tool_index = next((i for i, item in enumerate(self.active_tools) if item.id == tool.id), 0)
        self.recipe_index = 0
        self.render_tool()

    def render_search_results(self, query: str) -> None:
        tool_matches = [tool for tool in self.tools.search(query) if self.profiles.allows_tool(tool)]
        knowledge_matches = self.knowledge.search(query)
        query_lower = query.lower()
        asset_matches = [
            item for item in self.intelligence.list_assets(self.operations.active.id)
            if query_lower in item.value.lower() or query_lower in item.kind.lower() or query_lower in (item.label or "").lower()
        ]
        self.search_results = (
            [("tool", item) for item in tool_matches[:16]]
            + [("knowledge", item) for item in knowledge_matches[:12]]
            + [("asset", item) for item in asset_matches[:12]]
        )
        self.search_index = min(self.search_index, max(0, len(self.search_results) - 1))
        lines = []
        for index, (kind, item) in enumerate(self.search_results):
            marker = ">" if index == self.search_index else " "
            if kind == "tool":
                lines.append(f"{marker} TOOL   {item.name[:28]:<28} {item.category.upper()}")
            elif kind == "knowledge":
                lines.append(f"{marker} KNOW   {item.title[:28]:<28} {item.category.upper()}")
            else:
                lines.append(f"{marker} ASSET  {item.value[:28]:<28} {item.kind.upper()}")
        self.query_one("#body", OperatorPane).update("\n".join(lines) if lines else "NO MATCHES")
        self.set_header("FIELD//OS > SEARCH", f'SEARCH // "{query.upper()}"', f"{len(self.search_results)} combined result(s)", "↑↓ SELECT  ENTER OPEN  ESC BACK")
        self.focus_body()

    def action_help(self) -> None:
        if self.view != "help":
            self.return_view = self.view
        self.view = "help"
        self.hide_aux()
        self.query_one("#body", OperatorPane).update(
            "PRIMARY CONTROL\n"
            "↑ ↓        Navigate menu / list\n"
            "ENTER      Open / select / stage\n"
            "ESC        Back\n"
            "/          Global search\n\n"
            "FAST ACCESS\n"
            "F2         Terminal\n"
            "F3         Operations\n"
            "F4         Hardware status\n"
            "F5         Operation notes\n"
            "F9         Playbooks\n"
            "F10        Theme\n"
            "F11        Profile\n"
            "F12        Intelligence\n"
            "CTRL+Q     Exit FIELD//OS\n\n"
            "Commands remain review-first and completed commands are captured under the active operation."
        )
        self.set_header("FIELD//OS > HELP", "OPERATOR CONTROL", "Keyboard-first controls for RVN-01", "ESC BACK")
        self.focus_body()
