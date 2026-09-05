from __future__ import annotations

import asyncio
from datetime import datetime

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Input, RichLog, Static

from fieldos.hardware.mock import MockTelemetryProvider
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
    """FIELD//OS V0.3 — compact 800x480 operator console."""

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
    #search, #command { height: 3; border: tall #40484d; background: #090e11; }
    #search:focus, #command:focus { border: tall #ffffff; }
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
        Binding("f2", "terminal", "Terminal"),
        Binding("f4", "status", "Status"),
        Binding("f1", "help", "Help"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.telemetry_provider = MockTelemetryProvider()
        self.tools = ToolIndex.load_default()
        self.terminals = TerminalSessionManager()
        self.view = "home"
        self.category_index = 0
        self.tool_index = 0
        self.recipe_index = 0
        self.active_tools: list[ToolRecord] = []
        self.return_view = "home"

    def compose(self) -> ComposeResult:
        with Vertical(id="shell"):
            yield Static("RAVEN // FIELD//OS V0.3.0", id="status")
            yield Static("FIELD//OS", id="breadcrumb")
            yield Static("RAVEN", id="title")
            yield Static("FIELD OPERATIONS TERMINAL", id="description")
            yield Input(placeholder="SEARCH // tools, recipes, categories", id="search", classes="hidden")
            yield Static("", id="terminal-tabs", classes="hidden")
            yield OperatorPane("", id="body")
            yield Static("", id="example", classes="hidden")
            yield RichLog(id="terminal-output", wrap=True, markup=False, classes="hidden")
            yield Input(placeholder="rvn@fieldos $", id="command", classes="hidden")
            yield Static("↑↓ SELECT   → OPEN   / SEARCH   F2 TERMINAL   F4 STATUS", id="footer")

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
        self.query_one("#status", Static).update(
            f"RAVEN // FIELD//OS V0.3.0                         {mesh} {gps} {net}  BAT {t.battery_percent}%"
        )

    def hide_aux(self) -> None:
        for selector in ("#search", "#terminal-tabs", "#example", "#terminal-output", "#command"):
            self.query_one(selector).add_class("hidden")
        self.query_one("#body").remove_class("hidden")

    def render_home(self) -> None:
        self.view = "home"
        self.hide_aux()
        self.query_one("#breadcrumb", Static).update("FIELD//OS > HOME")
        self.query_one("#title", Static).update("MODULES")
        self.query_one("#description", Static).update("Select an operational library")
        lines = []
        for i, (name, desc) in enumerate(CATEGORIES):
            marker = ">" if i == self.category_index else " "
            count = len(self.tools.for_category(name.lower()))
            lines.append(f"{marker} {name:<12} {desc:<34} {count:02d}")
        self.query_one("#body", OperatorPane).update("\n".join(lines))
        self.query_one("#footer", Static).update("↑↓ SELECT   →/ENTER OPEN   / SEARCH   F2 TERMINAL   F4 STATUS")

    def render_library(self) -> None:
        self.view = "library"
        self.hide_aux()
        category, desc = CATEGORIES[self.category_index]
        self.active_tools = self.tools.for_category(category.lower())
        if self.active_tools:
            self.tool_index = min(self.tool_index, len(self.active_tools) - 1)
        else:
            self.tool_index = 0
        self.query_one("#breadcrumb", Static).update(f"FIELD//OS > {category}")
        self.query_one("#title", Static).update(f"{category} // LIBRARY")
        self.query_one("#description", Static).update(desc)
        lines = []
        for i, tool in enumerate(self.active_tools):
            marker = ">" if i == self.tool_index else " "
            state = "INST" if tool.installed else "----"
            lines.append(f"{marker} {tool.name:<24} {state:<4}  {(tool.subcategory or 'general').upper()}")
        if not lines:
            lines = ["NO TOOLS INDEXED"]
        self.query_one("#body", OperatorPane).update("\n".join(lines))
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

    def render_terminal(self) -> None:
        self.return_view = self.view if self.view != "terminal" else self.return_view
        self.view = "terminal"
        self.query_one("#body").add_class("hidden")
        self.query_one("#search").add_class("hidden")
        for selector in ("#terminal-tabs", "#example", "#terminal-output", "#command"):
            self.query_one(selector).remove_class("hidden")
        session = self.terminals.active
        tabs = []
        for i, item in enumerate(self.terminals.sessions):
            marker = ">" if i == self.terminals.active_index else " "
            busy = "*" if item.running else ""
            tabs.append(f"{marker}[{item.name}{busy}]")
        self.query_one("#terminal-tabs", Static).update("  ".join(tabs))
        self.query_one("#breadcrumb", Static).update("FIELD//OS > TERMINAL")
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
        self.query_one("#footer", Static).update("ESC BACK   TAB NEXT   SHIFT+TAB PREV   F6 NEW   F7 CLOSE   F8 CLEAR")

    def action_terminal(self) -> None:
        self.render_terminal()

    def action_status(self) -> None:
        self.return_view = self.view
        self.view = "status"
        self.hide_aux()
        t = self.telemetry_provider.read()
        self.query_one("#breadcrumb", Static).update("FIELD//OS > SYSTEM STATUS")
        self.query_one("#title", Static).update("RVN-01 // STATUS")
        self.query_one("#description", Static).update("Hardware and platform telemetry")
        self.query_one("#body", OperatorPane).update(
            f"MESH       {t.mesh}\nGPS        {t.gps}\nNETWORK    {t.network}\n"
            f"CPU TEMP   {t.cpu_temp_c:.1f} C\nSTORAGE    {t.storage_percent}%\nBATTERY    {t.battery_percent}%\n"
            f"TERMINALS  {len(self.terminals.sessions)}"
        )
        self.query_one("#footer", Static).update("ESC / ← BACK   F2 TERMINAL")

    def action_help(self) -> None:
        self.return_view = self.view
        self.view = "help"
        self.hide_aux()
        self.query_one("#breadcrumb", Static).update("FIELD//OS > HELP")
        self.query_one("#title", Static).update("KEYBOARD CONTROL")
        self.query_one("#description", Static).update("Context-first controls for the RVN-01 compact keyboard")
        self.query_one("#body", OperatorPane).update(
            "↑ ↓        Navigate\n→ / ENTER  Open / select\n← / ESC    Back\n/          Search\n"
            "F2         Terminal\nF4         System status\nF6         New terminal (terminal screen)\n"
            "F7         Close terminal\nF8         Clear terminal\nTAB        Next terminal\nSHIFT+TAB  Previous terminal"
        )
        self.query_one("#footer", Static).update("ESC / ← BACK")

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
        elif self.view == "terminal" and self.query_one("#command", Input).has_focus:
            self.history_up()

    def action_move_down(self) -> None:
        if self.view == "home":
            self.category_index = min(len(CATEGORIES)-1, self.category_index + 1); self.render_home()
        elif self.view == "library" and self.active_tools:
            self.tool_index = min(len(self.active_tools)-1, self.tool_index + 1); self.render_library()
        elif self.view == "tool" and self.active_tools and self.active_tools[self.tool_index].recipes:
            recipes = self.active_tools[self.tool_index].recipes
            self.recipe_index = min(len(recipes)-1, self.recipe_index + 1); self.render_tool()
        elif self.view == "terminal" and self.query_one("#command", Input).has_focus:
            self.history_down()

    def action_open(self) -> None:
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

    def action_back(self) -> None:
        if self.view == "terminal":
            self.restore_view(self.return_view); return
        if self.view in {"search", "status", "help"}:
            self.restore_view(self.return_view); return
        if self.view == "tool": self.render_library()
        elif self.view == "library": self.render_home()

    def restore_view(self, view: str) -> None:
        if view == "tool": self.render_tool()
        elif view == "library": self.render_library()
        else: self.render_home()
        self.query_one("#body", OperatorPane).focus()

    def stage_command(self, command: str, label: str, tool: ToolRecord) -> None:
        session = self.terminals.active
        if session.tool_id not in {None, tool.id}:
            session = self.terminals.create_for_tool(tool.id, tool.name)
        else:
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
            process = await asyncio.create_subprocess_shell(command, cwd=session.cwd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
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
