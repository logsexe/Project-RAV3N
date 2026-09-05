from __future__ import annotations

import asyncio
from datetime import datetime

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Input, RichLog, Static

from fieldos.hardware.mock import MockTelemetryProvider
from fieldos.operations import OperationSessionManager
from fieldos.playbooks import PlaybookIndex
from fieldos.sessions import TerminalSessionManager
from fieldos.tools import ToolIndex, ToolRecord

CATEGORIES = [
    ("BLUE", "Defensive security / hunting"),
    ("RED", "Authorised testing / validation"),
    ("NETWORK", "Discovery / packet analysis"),
    ("FORENSICS", "DFIR / evidence analysis"),
    ("FIELD", "Sessions / notes / navigation"),
    ("COMMS", "Meshtastic / messaging"),
    ("HARDWARE", "USB / serial / electronics"),
    ("RF", "SDR / spectrum tools"),
    ("UTILITIES", "Operator utilities"),
]


class OperatorPane(Static):
    can_focus = True


class FieldOSApp(App[None]):
    """FIELD//OS V0.4 — compact field operations console."""

    TITLE = "RAVEN // FIELD//OS"
    CSS = """
    Screen { background: #050809; color: #d7ddd9; }
    #shell { height: 1fr; padding: 0 1; }
    #status { height: 1; color: #aeb8bc; background: #0c1114; text-style: bold; }
    #breadcrumb { height: 1; color: #657178; }
    #title { height: 2; color: #ffffff; text-style: bold; padding-top: 1; }
    #description { height: 2; color: #87939a; }
    #body { height: 1fr; padding: 1 2; border: solid #263137; background: #080d0f; }
    #body:focus { border: heavy #d7ddd9; background: #0c1317; }
    #example { height: 2; color: #89959b; padding: 0 1; }
    #search, #entry, #command { height: 3; border: tall #40484d; background: #090e11; }
    #search:focus, #entry:focus, #command:focus { border: tall #ffffff; }
    #terminal-tabs { height: 1; color: #d7ddd9; text-style: bold; }
    #terminal-output { height: 1fr; padding: 0 1; border: solid #263137; background: #030506; }
    #footer { height: 1; color: #aeb8bc; background: #0c1114; text-align: center; }
    .hidden { display: none; }
    """

    BINDINGS = [
        Binding("up", "move_up", show=False),
        Binding("down", "move_down", show=False),
        Binding("right", "open", show=False),
        Binding("enter", "open", show=False),
        Binding("left", "back", show=False),
        Binding("escape", "back", show=False),
        Binding("/", "search", show=False),
        Binding("f1", "help", "Help"),
        Binding("f2", "terminal", "Terminal"),
        Binding("f3", "sessions", "Sessions"),
        Binding("f4", "status", "Status"),
        Binding("f5", "notes", "Notes"),
        Binding("f9", "playbooks", "Playbooks"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.telemetry_provider = MockTelemetryProvider()
        self.tools = ToolIndex.load_default()
        self.terminals = TerminalSessionManager()
        self.operations = OperationSessionManager()
        self.playbooks = PlaybookIndex.load_default()
        self.view = "home"
        self.return_view = "home"
        self.entry_mode: str | None = None
        self.category_index = 0
        self.tool_index = 0
        self.recipe_index = 0
        self.operation_index = self.operations.active_index
        self.playbook_index = 0
        self.playbook_step_index = 0
        self.active_tools: list[ToolRecord] = []

    def compose(self) -> ComposeResult:
        with Vertical(id="shell"):
            yield Static("RAVEN // FIELD//OS V0.4.0", id="status")
            yield Static("FIELD//OS", id="breadcrumb")
            yield Static("RAVEN", id="title")
            yield Static("FIELD OPERATIONS TERMINAL", id="description")
            yield Input(placeholder="SEARCH // tools, recipes, categories", id="search", classes="hidden")
            yield Input(placeholder="ENTRY", id="entry", classes="hidden")
            yield Static("", id="terminal-tabs", classes="hidden")
            yield OperatorPane("", id="body")
            yield Static("", id="example", classes="hidden")
            yield RichLog(id="terminal-output", wrap=True, markup=False, classes="hidden")
            yield Input(placeholder="rvn@fieldos $", id="command", classes="hidden")
            yield Static("↑↓ SELECT   → OPEN   / SEARCH   F2 TERM   F3 SESS   F5 NOTES", id="footer")

    def on_mount(self) -> None:
        self.set_interval(1.5, self.refresh_status)
        self.query_one("#body", OperatorPane).focus()
        self.render_home()
        self.refresh_status()

    def refresh_status(self) -> None:
        t = self.telemetry_provider.read()
        mesh = "M●" if str(t.mesh).upper() not in {"OFF", "NOT PRESENT", "DISCONNECTED"} else "M○"
        gps = "G●" if str(t.gps).upper() not in {"OFF", "NOT PRESENT", "DISCONNECTED"} else "G○"
        net = "N●" if str(t.network).upper() not in {"OFF", "NOT PRESENT", "DISCONNECTED"} else "N○"
        op = self.operations.active.id
        self.query_one("#status", Static).update(
            f"RAVEN // {op:<14}                     {mesh} {gps} {net} BAT {t.battery_percent}%"
        )

    def hide_aux(self) -> None:
        for selector in ("#search", "#entry", "#terminal-tabs", "#example", "#terminal-output", "#command"):
            self.query_one(selector).add_class("hidden")
        self.query_one("#body").remove_class("hidden")
        self.entry_mode = None

    def focus_body(self) -> None:
        self.query_one("#body", OperatorPane).focus()

    def render_home(self) -> None:
        self.view = "home"
        self.hide_aux()
        self.query_one("#breadcrumb", Static).update("FIELD//OS > HOME")
        self.query_one("#title", Static).update("MODULES")
        self.query_one("#description", Static).update(
            f"ACTIVE OPERATION // {self.operations.active.id} // {self.operations.active.name}"
        )
        lines = []
        for i, (name, desc) in enumerate(CATEGORIES):
            marker = ">" if i == self.category_index else " "
            count = len(self.tools.for_category(name.lower()))
            lines.append(f"{marker} {name:<12} {desc:<34} {count:02d}")
        self.query_one("#body", OperatorPane).update("\n".join(lines))
        self.query_one("#footer", Static).update("↑↓ SELECT  → OPEN  / SEARCH  F2 TERM  F3 SESS  F5 NOTES  F9 PLAY")

    def render_library(self) -> None:
        self.view = "library"
        self.hide_aux()
        category, desc = CATEGORIES[self.category_index]
        self.active_tools = self.tools.for_category(category.lower())
        self.tool_index = min(self.tool_index, max(0, len(self.active_tools) - 1))
        self.query_one("#breadcrumb", Static).update(f"FIELD//OS > {category}")
        self.query_one("#title", Static).update(f"{category} // LIBRARY")
        self.query_one("#description", Static).update(desc)
        lines = []
        for i, tool in enumerate(self.active_tools):
            marker = ">" if i == self.tool_index else " "
            state = "INST" if tool.installed else "----"
            lines.append(f"{marker} {tool.name:<24} {state:<4}  {(tool.subcategory or 'general').upper()}")
        self.query_one("#body", OperatorPane).update("\n".join(lines) if lines else "NO TOOLS INDEXED")
        self.query_one("#footer", Static).update("← BACK   ↑↓ SELECT   →/ENTER OPEN   / SEARCH   F2 TERMINAL")

    def render_tool(self) -> None:
        if not self.active_tools:
            return
        self.view = "tool"
        self.hide_aux()
        tool = self.active_tools[self.tool_index]
        self.query_one("#breadcrumb", Static).update(f"FIELD//OS > {tool.category.upper()} > {tool.name.upper()}")
        self.query_one("#title", Static).update(tool.name.upper())
        self.query_one("#description", Static).update(tool.description or "FIELD//OS indexed tool")
        lines = [
            f"STATUS       {'INSTALLED' if tool.installed else 'AVAILABLE'}",
            f"COMMAND      {tool.command or 'N/A'}",
            f"PRIORITY     {tool.priority.upper()}",
            f"MODE         {'AUTHORISED USE' if tool.authorised_use_only else 'STANDARD'}",
            "",
        ]
        if tool.recipes:
            lines.append("RECIPES")
            for i, recipe in enumerate(tool.recipes):
                marker = ">" if i == self.recipe_index else " "
                lines.append(f"{marker} {recipe.name}")
        else:
            lines.append("> CUSTOM COMMAND / BASE COMMAND")
        self.query_one("#body", OperatorPane).update("\n".join(lines))
        self.query_one("#footer", Static).update("← BACK   ↑↓ RECIPE   →/ENTER STAGE   F2 TERMINAL")

    def action_sessions(self) -> None:
        if self.view != "sessions":
            self.return_view = self.view
        self.render_sessions()

    def render_sessions(self) -> None:
        self.view = "sessions"
        self.hide_aux()
        self.operation_index = min(self.operation_index, len(self.operations.sessions) - 1)
        self.query_one("#breadcrumb", Static).update("FIELD//OS > OPERATIONS")
        self.query_one("#title", Static).update("FIELD SESSIONS")
        self.query_one("#description", Static).update("Persistent cases / exercises / field operations")
        lines = []
        for i, item in enumerate(self.operations.sessions):
            marker = ">" if i == self.operation_index else " "
            active = "ACTIVE" if i == self.operations.active_index else ""
            lines.append(f"{marker} {item.id:<18} {item.name:<26} {active}")
        lines.extend(["", f"DATA // {self.operations.root}"])
        self.query_one("#body", OperatorPane).update("\n".join(lines))
        self.query_one("#footer", Static).update("ESC BACK   ↑↓ SELECT   ENTER ACTIVATE   N NEW SESSION")
        self.focus_body()

    def start_session_entry(self) -> None:
        self.entry_mode = "new-session"
        entry = self.query_one("#entry", Input)
        entry.placeholder = "NEW SESSION NAME // e.g. INC-001 or WIRELESS-SURVEY"
        entry.value = ""
        entry.remove_class("hidden")
        entry.focus()

    def action_notes(self) -> None:
        if self.view != "notes":
            self.return_view = self.view
        self.render_notes()

    def render_notes(self) -> None:
        self.view = "notes"
        self.hide_aux()
        op = self.operations.active
        self.query_one("#breadcrumb", Static).update(f"FIELD//OS > {op.id} > NOTES")
        self.query_one("#title", Static).update("OPERATION NOTES")
        self.query_one("#description", Static).update(f"{op.name} // {len(op.notes)} timeline entries")
        notes = op.notes[-14:]
        body = "\n".join(notes) if notes else "NO NOTES YET\n\nPress N to add a timestamped operation note."
        self.query_one("#body", OperatorPane).update(body)
        self.query_one("#footer", Static).update("ESC BACK   N NEW NOTE   F3 SESSIONS   F2 TERMINAL")
        self.focus_body()

    def start_note_entry(self) -> None:
        self.entry_mode = "note"
        entry = self.query_one("#entry", Input)
        entry.placeholder = "ADD TIMESTAMPED OPERATION NOTE"
        entry.value = ""
        entry.remove_class("hidden")
        entry.focus()

    def action_playbooks(self) -> None:
        if self.view not in {"playbooks", "playbook"}:
            self.return_view = self.view
        self.render_playbooks()

    def render_playbooks(self) -> None:
        self.view = "playbooks"
        self.hide_aux()
        items = self.playbooks.all
        self.playbook_index = min(self.playbook_index, max(0, len(items) - 1))
        self.query_one("#breadcrumb", Static).update("FIELD//OS > PLAYBOOKS")
        self.query_one("#title", Static).update("OPERATOR PLAYBOOKS")
        self.query_one("#description", Static).update("Guided, review-first field workflows")
        lines = []
        for i, playbook in enumerate(items):
            marker = ">" if i == self.playbook_index else " "
            lines.append(f"{marker} {playbook.name:<24} {playbook.category.upper():<10} {len(playbook.steps):02d} STEPS")
        self.query_one("#body", OperatorPane).update("\n".join(lines) if lines else "NO PLAYBOOKS INDEXED")
        self.query_one("#footer", Static).update("ESC BACK   ↑↓ SELECT   →/ENTER OPEN")
        self.focus_body()

    def render_playbook(self) -> None:
        items = self.playbooks.all
        if not items:
            return
        self.view = "playbook"
        self.hide_aux()
        playbook = items[self.playbook_index]
        self.playbook_step_index = min(self.playbook_step_index, max(0, len(playbook.steps) - 1))
        self.query_one("#breadcrumb", Static).update(f"FIELD//OS > PLAYBOOKS > {playbook.name.upper()}")
        self.query_one("#title", Static).update(playbook.name.upper())
        self.query_one("#description", Static).update(playbook.description)
        lines = []
        for i, step in enumerate(playbook.steps):
            marker = ">" if i == self.playbook_step_index else " "
            lines.append(f"{marker} {i + 1:02d} // {step.name}")
            if i == self.playbook_step_index:
                if step.description:
                    lines.append(f"     {step.description}")
                if step.command:
                    lines.append(f"     $ {step.command}")
                elif step.tool:
                    lines.append(f"     TOOL // {step.tool}")
            lines.append("")
        self.query_one("#body", OperatorPane).update("\n".join(lines).rstrip())
        self.query_one("#footer", Static).update("ESC BACK   ↑↓ STEP   →/ENTER STAGE COMMAND   F5 NOTES")
        self.focus_body()

    def render_terminal(self) -> None:
        self.return_view = self.view if self.view != "terminal" else self.return_view
        self.view = "terminal"
        self.query_one("#body").add_class("hidden")
        self.query_one("#search").add_class("hidden")
        self.query_one("#entry").add_class("hidden")
        for selector in ("#terminal-tabs", "#example", "#terminal-output", "#command"):
            self.query_one(selector).remove_class("hidden")
        session = self.terminals.active
        tabs = []
        for i, item in enumerate(self.terminals.sessions):
            marker = ">" if i == self.terminals.active_index else " "
            busy = "*" if item.running else ""
            tabs.append(f"{marker}[{item.name}{busy}]")
        self.query_one("#terminal-tabs", Static).update("  ".join(tabs))
        self.query_one("#breadcrumb", Static).update(f"FIELD//OS > {self.operations.active.id} > TERMINAL")
        self.query_one("#title", Static).update(f"{session.name} // {'BUSY' if session.running else 'READY'}")
        self.query_one("#description", Static).update(f"CWD // {session.cwd}")
        example = session.staged_label or "CUSTOM COMMANDS ENABLED"
        command = session.staged_command or "Type any local shell command below"
        self.query_one("#example", Static).update(f"{example}\n$ {command}")
        log = self.query_one("#terminal-output", RichLog)
        log.clear()
        for line in session.output:
            log.write(line)
        command_input = self.query_one("#command", Input)
        command_input.value = session.staged_command
        command_input.cursor_position = len(command_input.value)
        command_input.focus()
        self.query_one("#footer", Static).update("ESC BACK  TAB NEXT  SHIFT+TAB PREV  F6 NEW  F7 CLOSE  F8 CLEAR")

    def action_terminal(self) -> None:
        self.render_terminal()

    def action_status(self) -> None:
        if self.view != "status":
            self.return_view = self.view
        self.view = "status"
        self.hide_aux()
        t = self.telemetry_provider.read()
        self.query_one("#breadcrumb", Static).update("FIELD//OS > SYSTEM STATUS")
        self.query_one("#title", Static).update("RVN-01 // STATUS")
        self.query_one("#description", Static).update("Hardware and platform telemetry")
        self.query_one("#body", OperatorPane).update(
            f"OPERATION  {self.operations.active.id}\nMESH       {t.mesh}\nGPS        {t.gps}\nNETWORK    {t.network}\n"
            f"CPU TEMP   {t.cpu_temp_c:.1f} C\nSTORAGE    {t.storage_percent}%\nBATTERY    {t.battery_percent}%\n"
            f"TERMINALS  {len(self.terminals.sessions)}\nPLAYBOOKS  {len(self.playbooks.all)}"
        )
        self.query_one("#footer", Static).update("ESC / ← BACK   F2 TERMINAL   F3 SESSIONS")
        self.focus_body()

    def action_help(self) -> None:
        if self.view != "help":
            self.return_view = self.view
        self.view = "help"
        self.hide_aux()
        self.query_one("#breadcrumb", Static).update("FIELD//OS > HELP")
        self.query_one("#title", Static).update("KEYBOARD CONTROL")
        self.query_one("#description", Static).update("Context-first controls for RVN-01")
        self.query_one("#body", OperatorPane).update(
            "↑ ↓        Navigate\n→ / ENTER  Open / select\n← / ESC    Back\n/          Search\n"
            "F2         Terminal\nF3         Operations / sessions\nF4         System status\n"
            "F5         Operation notes\nF9         Playbooks\n\nTERMINAL\n"
            "TAB        Next terminal\nSHIFT+TAB  Previous terminal\nF6         New terminal\nF7         Close terminal\nF8         Clear terminal"
        )
        self.query_one("#footer", Static).update("ESC / ← BACK")
        self.focus_body()

    def action_search(self) -> None:
        if self.view == "terminal":
            return
        self.return_view = self.view
        self.view = "search"
        self.hide_aux()
        search = self.query_one("#search", Input)
        search.remove_class("hidden")
        self.query_one("#breadcrumb", Static).update("FIELD//OS > SEARCH")
        self.query_one("#title", Static).update("GLOBAL SEARCH")
        self.query_one("#description", Static).update("Search tools, recipes, categories and commands")
        self.query_one("#body", OperatorPane).update("TYPE QUERY ABOVE // ENTER SEARCH")
        search.focus()
        self.query_one("#footer", Static).update("ENTER SEARCH   ESC BACK")

    def action_move_up(self) -> None:
        if self.view == "home":
            self.category_index = max(0, self.category_index - 1); self.render_home()
        elif self.view == "library" and self.active_tools:
            self.tool_index = max(0, self.tool_index - 1); self.render_library()
        elif self.view == "tool" and self.active_tools and self.active_tools[self.tool_index].recipes:
            self.recipe_index = max(0, self.recipe_index - 1); self.render_tool()
        elif self.view == "sessions":
            self.operation_index = max(0, self.operation_index - 1); self.render_sessions()
        elif self.view == "playbooks":
            self.playbook_index = max(0, self.playbook_index - 1); self.render_playbooks()
        elif self.view == "playbook" and self.playbooks.all:
            self.playbook_step_index = max(0, self.playbook_step_index - 1); self.render_playbook()
        elif self.view == "terminal" and self.query_one("#command", Input).has_focus:
            self.history_up()

    def action_move_down(self) -> None:
        if self.view == "home":
            self.category_index = min(len(CATEGORIES) - 1, self.category_index + 1); self.render_home()
        elif self.view == "library" and self.active_tools:
            self.tool_index = min(len(self.active_tools) - 1, self.tool_index + 1); self.render_library()
        elif self.view == "tool" and self.active_tools and self.active_tools[self.tool_index].recipes:
            recipes = self.active_tools[self.tool_index].recipes
            self.recipe_index = min(len(recipes) - 1, self.recipe_index + 1); self.render_tool()
        elif self.view == "sessions":
            self.operation_index = min(len(self.operations.sessions) - 1, self.operation_index + 1); self.render_sessions()
        elif self.view == "playbooks":
            self.playbook_index = min(len(self.playbooks.all) - 1, self.playbook_index + 1); self.render_playbooks()
        elif self.view == "playbook" and self.playbooks.all:
            steps = self.playbooks.all[self.playbook_index].steps
            self.playbook_step_index = min(len(steps) - 1, self.playbook_step_index + 1); self.render_playbook()
        elif self.view == "terminal" and self.query_one("#command", Input).has_focus:
            self.history_down()

    def action_open(self) -> None:
        if isinstance(self.focused, Input):
            return
        if self.view == "home":
            self.tool_index = 0; self.render_library()
        elif self.view == "library" and self.active_tools:
            self.recipe_index = 0; self.render_tool()
        elif self.view == "tool" and self.active_tools:
            tool = self.active_tools[self.tool_index]
            if tool.recipes:
                recipe = tool.recipes[self.recipe_index]
                self.stage_command(recipe.command, f"EXAMPLE // {tool.name} // {recipe.name}", tool)
            elif tool.command:
                self.stage_command(tool.command, f"EXAMPLE // {tool.name} // BASE COMMAND", tool)
        elif self.view == "sessions":
            self.operations.select(self.operation_index)
            self.operation_index = self.operations.active_index
            self.refresh_status()
            self.render_sessions()
        elif self.view == "playbooks":
            self.playbook_step_index = 0; self.render_playbook()
        elif self.view == "playbook" and self.playbooks.all:
            step = self.playbooks.all[self.playbook_index].steps[self.playbook_step_index]
            if step.command:
                self.stage_command(step.command, f"PLAYBOOK // {self.playbooks.all[self.playbook_index].name} // {step.name}")
            else:
                self.operations.add_note(f"PLAYBOOK STEP // {self.playbooks.all[self.playbook_index].name} // {step.name}")
                self.notify("STEP ADDED TO OPERATION NOTES", title="PLAYBOOK", timeout=1.5)

    def action_back(self) -> None:
        if isinstance(self.focused, Input):
            if self.focused.id in {"search", "entry", "command"}:
                self.restore_view(self.return_view)
                return
        if self.view == "terminal":
            self.restore_view(self.return_view); return
        if self.view in {"search", "status", "help", "sessions", "notes", "playbooks"}:
            self.restore_view(self.return_view); return
        if self.view == "playbook":
            self.render_playbooks(); return
        if self.view == "tool": self.render_library()
        elif self.view == "library": self.render_home()

    def restore_view(self, view: str) -> None:
        if view == "tool": self.render_tool()
        elif view == "library": self.render_library()
        elif view == "sessions": self.render_sessions()
        elif view == "notes": self.render_notes()
        elif view == "playbooks": self.render_playbooks()
        elif view == "playbook": self.render_playbook()
        else: self.render_home()
        self.focus_body()

    def stage_command(self, command: str, label: str, tool: ToolRecord | None = None) -> None:
        session = self.terminals.active
        if tool and session.tool_id not in {None, tool.id}:
            session = self.terminals.create_for_tool(tool.id, tool.name)
        elif tool:
            session.tool_id, session.tool_name = tool.id, tool.name
        session.staged_command, session.staged_label = command, label
        self.render_terminal()

    def history_up(self) -> None:
        s = self.terminals.active
        if not s.history: return
        s.history_index = max(0, s.history_index - 1)
        self.query_one("#command", Input).value = s.history[s.history_index]

    def history_down(self) -> None:
        s = self.terminals.active
        if not s.history: return
        s.history_index = min(len(s.history), s.history_index + 1)
        self.query_one("#command", Input).value = "" if s.history_index >= len(s.history) else s.history[s.history_index]

    def on_key(self, event) -> None:
        body_focused = isinstance(self.focused, OperatorPane)
        if body_focused and self.view == "sessions" and event.key == "n":
            event.prevent_default(); event.stop(); self.start_session_entry(); return
        if body_focused and self.view == "notes" and event.key == "n":
            event.prevent_default(); event.stop(); self.start_note_entry(); return
        if self.view != "terminal" or not self.query_one("#command", Input).has_focus:
            return
        if event.key == "tab":
            event.prevent_default(); event.stop(); self.terminals.next(); self.render_terminal()
        elif event.key == "shift+tab":
            event.prevent_default(); event.stop(); self.terminals.previous(); self.render_terminal()
        elif event.key == "f6":
            event.prevent_default(); event.stop(); self.terminals.create(); self.render_terminal()
        elif event.key == "f7":
            event.prevent_default(); event.stop(); self.terminals.close_active(); self.render_terminal()
        elif event.key == "f8":
            event.prevent_default(); event.stop(); self.terminals.active.output.clear(); self.terminals.active.append("TERMINAL BUFFER CLEARED"); self.render_terminal()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "command":
            command = event.value.strip()
            if not command: return
            session = self.terminals.active
            session.push_history(command)
            session.staged_command = ""
            event.input.value = ""
            asyncio.create_task(self.run_command(command, session))
            return
        if event.input.id == "entry":
            value = event.value.strip()
            if self.entry_mode == "new-session" and value:
                self.operations.create(value)
                self.operation_index = self.operations.active_index
                self.refresh_status()
                self.render_sessions()
            elif self.entry_mode == "note" and value:
                self.operations.add_note(value)
                self.render_notes()
            return
        if event.input.id == "search":
            query = event.value.strip()
            if not query: return
            matches = self.tools.search(query)
            lines = [f"> {t.name:<24} {t.category.upper():<10} {'INST' if t.installed else '----'}" for t in matches[:20]]
            self.query_one("#body", OperatorPane).update("\n".join(lines) if lines else "NO MATCHES")

    async def run_command(self, command: str, session) -> None:
        if session.running:
            session.append("BUSY // command already running"); self.render_terminal(); return
        session.running = True
        session.append(f"[{datetime.now().strftime('%H:%M:%S')}] rvn@fieldos $ {command}")
        self.render_terminal()
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=session.cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            assert process.stdout is not None
            while True:
                raw = await process.stdout.readline()
                if not raw: break
                session.append(raw.decode(errors="replace").rstrip())
                if session is self.terminals.active and self.view == "terminal":
                    self.query_one("#terminal-output", RichLog).write(session.output[-1])
            code = await process.wait()
            session.append(f"[exit {code}] // command complete")
        except Exception as exc:
            session.append(f"[terminal error] {exc}")
        finally:
            session.running = False
            if session is self.terminals.active and self.view == "terminal": self.render_terminal()


if __name__ == "__main__":
    FieldOSApp().run()
