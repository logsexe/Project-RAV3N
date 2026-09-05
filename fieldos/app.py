from __future__ import annotations

import asyncio
import os
from datetime import datetime

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, Label, ListItem, ListView, RichLog, Static

from fieldos.hardware.mock import MockTelemetryProvider
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
    """Focusable FIELD//OS operator pane."""

    can_focus = True


class FieldOSApp(App[None]):
    """FIELD//OS V0.2.1 development operator console."""

    TITLE = "RAVEN // RVN-01 // FIELD//OS"
    SUB_TITLE = "FIELD OPERATIONS TERMINAL // DEVELOPMENT UNIT"

    CSS = """
    Screen {
        background: #070a0c;
        color: #d7ddd9;
    }

    Header {
        background: #0c1114;
        color: #d7ddd9;
        border-bottom: solid #586067;
    }

    #shell {
        height: 1fr;
        padding: 1 2;
    }

    #identity {
        height: auto;
        margin-bottom: 1;
    }

    #platform {
        text-style: bold;
        color: #f0f2ef;
    }

    #designation, #modebar {
        color: #7f8b91;
    }

    #modebar {
        height: 1;
        margin-bottom: 1;
    }

    #search {
        margin: 0 0 1 0;
        border: tall #40484d;
        background: #0b1013;
    }

    #search:focus {
        border: tall #d7ddd9;
    }

    #workspace {
        height: 1fr;
    }

    #category-list {
        width: 31;
        min-width: 25;
        height: 1fr;
        background: #0a0f12;
        border-right: solid #343c41;
        padding-right: 1;
    }

    #category-list > ListItem {
        height: 3;
        padding: 0 1;
        color: #879198;
        background: #0a0f12;
        border-left: solid #151c20;
    }

    #category-list > ListItem.active {
        color: #ffffff;
        background: #283238;
        text-style: bold;
        border-left: heavy #d7ddd9;
    }

    #category-list:focus > ListItem.active {
        background: #3b4850;
        border-left: heavy #ffffff;
    }

    .category-title {
        width: 1fr;
    }

    #content {
        width: 1fr;
        height: 1fr;
        padding: 0 1 0 2;
        border-left: solid #151c20;
    }

    #content:focus-within {
        background: #0c1215;
        border-left: heavy #8e9aa0;
    }

    #breadcrumb {
        height: 1;
        color: #647078;
    }

    #content-title {
        height: 2;
        color: #f0f2ef;
        text-style: bold;
    }

    #content-description {
        height: 2;
        color: #89959b;
    }

    #content-body {
        height: 1fr;
        min-height: 8;
        padding: 1 1;
        color: #c3cbce;
        border: solid #252e33;
    }

    #content-body:focus {
        color: #ffffff;
        background: #10181c;
        border: heavy #b5c0c5;
    }

    #nav-hint {
        height: 1;
        color: #68747a;
    }

    #terminal-shell {
        height: 13;
        margin-top: 1;
        padding: 0 1;
        background: #080d0f;
        border: solid #303a3f;
    }

    #terminal-title {
        height: 1;
        color: #d7ddd9;
        text-style: bold;
    }

    #terminal-example {
        height: 2;
        color: #7f8b91;
    }

    #terminal-output {
        height: 1fr;
        background: #050809;
        color: #c9d0d2;
        border: solid #1f282c;
        padding: 0 1;
    }

    #command-input {
        height: 3;
        margin-top: 1;
        border: tall #40484d;
        background: #0a0f12;
    }

    #command-input:focus {
        border: tall #ffffff;
        background: #11191d;
    }

    #telemetry {
        height: 3;
        margin-top: 1;
        padding: 0 1;
        background: #0c1114;
        border-top: solid #394146;
        border-bottom: solid #394146;
        content-align: center middle;
        color: #aeb8bc;
    }

    #mission {
        height: 1;
        margin-top: 1;
        color: #5f6a70;
        text-align: center;
    }

    Footer {
        background: #0c1114;
        color: #7f8b91;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("/", "search", "Search"),
        Binding("escape", "dashboard", "Dashboard"),
        Binding("right", "go_deeper", "Open", show=False),
        Binding("left", "go_back", "Back", show=False),
        Binding("up", "move_up", "Previous", show=False),
        Binding("down", "move_down", "Next", show=False),
        Binding("enter", "go_deeper", "Select", show=False),
        Binding("ctrl+t", "terminal", "Terminal"),
        Binding("ctrl+l", "clear_terminal", "Clear terminal"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.telemetry_provider = MockTelemetryProvider()
        self.tools = ToolIndex.load_default()
        self.active_category_index = 0
        self.active_tools: list[ToolRecord] = []
        self.active_tool_index = 0
        self.active_recipe_index = 0
        self.depth = "category"
        self.command_history: list[str] = []
        self.command_history_index = 0
        self.command_running = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Vertical(id="shell"):
            with Vertical(id="identity"):
                yield Static("RAVEN // RVN-01", id="platform")
                yield Static(
                    "FIELD OPERATIONS TERMINAL // HW REV A // FIELD//OS V0.2.1",
                    id="designation",
                )
                yield Static("", id="modebar")

            yield Input(
                placeholder="SEARCH // tools, recipes, categories, knowledge",
                id="search",
            )

            with Horizontal(id="workspace"):
                yield ListView(
                    *[
                        ListItem(
                            Label(f"{name}\n{description}", classes="category-title"),
                            id=f"category-{name.lower()}",
                        )
                        for name, description in CATEGORIES
                    ],
                    id="category-list",
                )

                with Vertical(id="content"):
                    yield Static("FIELD//OS > BLUE", id="breadcrumb")
                    yield Static("BLUE // MODULE", id="content-title")
                    yield Static("Defensive security / hunting", id="content-description")
                    yield OperatorPane("", id="content-body")
                    yield Static("", id="nav-hint")

                    with Vertical(id="terminal-shell"):
                        yield Static("LOCAL TERMINAL // READY", id="terminal-title")
                        yield Static(
                            "EXAMPLE // select a recipe to stage its command here",
                            id="terminal-example",
                        )
                        yield RichLog(id="terminal-output", wrap=True, markup=False)
                        yield Input(
                            placeholder="rvn@fieldos $ type any local shell command",
                            id="command-input",
                        )

            yield Static("SYSTEM TELEMETRY INITIALISING", id="telemetry")
            yield Static("RECON // ANALYSE // OPERATE", id="mission")

        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(1.5, self.refresh_telemetry)
        self.refresh_telemetry()
        category_list = self.query_one("#category-list", ListView)
        category_list.index = 0
        category_list.focus()
        self.set_active_category(0)
        self.render_category("BLUE")
        self.refresh_modebar()
        self.write_terminal("FIELD//OS LOCAL SHELL ONLINE")
        self.write_terminal(f"CWD // {os.getcwd()}")
        self.write_terminal("CTRL+T focuses terminal // type any local command // ENTER executes")

    def refresh_modebar(self) -> None:
        installed = self.tools.installed_count()
        total = len(self.tools.all)
        self.query_one("#modebar", Static).update(
            f"MODE FIELD // MANIFEST {total:02d} TOOLS // DETECTED {installed:02d} // PROFILE DEVELOPMENT"
        )

    def refresh_telemetry(self) -> None:
        telemetry = self.telemetry_provider.read()
        line = (
            f"MESH {telemetry.mesh}   //   "
            f"GPS {telemetry.gps}   //   "
            f"NET {telemetry.network}   //   "
            f"CPU {telemetry.cpu_temp_c:.1f}C   //   "
            f"STG {telemetry.storage_percent}%   //   "
            f"BAT {telemetry.battery_percent}%"
        )
        self.query_one("#telemetry", Static).update(line)

    def action_search(self) -> None:
        if isinstance(self.focused, Input) and self.focused.id == "command-input":
            return
        self.query_one("#search", Input).focus()

    def action_terminal(self) -> None:
        self.query_one("#command-input", Input).focus()

    def action_clear_terminal(self) -> None:
        self.query_one("#terminal-output", RichLog).clear()
        self.write_terminal("TERMINAL BUFFER CLEARED")

    def action_dashboard(self) -> None:
        if isinstance(self.focused, Input) and self.focused.id == "command-input":
            self.query_one("#content-body", OperatorPane).focus()
            return
        search = self.query_one("#search", Input)
        search.value = ""
        category_list = self.query_one("#category-list", ListView)
        category_list.focus()
        self.depth = "category"
        index = category_list.index if category_list.index is not None else self.active_category_index
        self.set_active_category(index)
        self.render_category(CATEGORIES[index][0])

    def action_go_deeper(self) -> None:
        if isinstance(self.focused, Input):
            return

        if self.depth == "category":
            if not self.active_tools:
                self.notify("MODULE LIBRARY // EMPTY", title="FIELD//OS", timeout=1.5)
                return
            self.depth = "tools"
            self.query_one("#content-body", OperatorPane).focus()
            self.render_tool_list()
            return

        if self.depth == "tools" and self.active_tools:
            self.depth = "detail"
            self.active_recipe_index = 0
            self.render_tool_detail(self.active_tools[self.active_tool_index])
            return

        if self.depth == "detail" and self.active_tools:
            tool = self.active_tools[self.active_tool_index]
            if not tool.recipes:
                self.stage_tool_command(tool)
                return
            self.depth = "recipes"
            self.active_recipe_index = 0
            self.render_recipes(tool)
            return

        if self.depth == "recipes" and self.active_tools:
            tool = self.active_tools[self.active_tool_index]
            if tool.recipes:
                recipe = tool.recipes[self.active_recipe_index]
                self.stage_command(recipe.command, f"{tool.name} // {recipe.name}")

    def action_go_back(self) -> None:
        if isinstance(self.focused, Input):
            if self.focused.id == "command-input":
                self.query_one("#content-body", OperatorPane).focus()
                return
            self.action_dashboard()
            return

        if self.depth == "recipes":
            self.depth = "detail"
            self.render_tool_detail(self.active_tools[self.active_tool_index])
            return

        if self.depth == "detail":
            self.depth = "tools"
            self.render_tool_list()
            return

        if self.depth == "tools":
            self.depth = "category"
            self.query_one("#category-list", ListView).focus()
            self.render_category(CATEGORIES[self.active_category_index][0])

    def action_move_up(self) -> None:
        if isinstance(self.focused, Input):
            if self.focused.id == "command-input":
                self.command_history_up()
            return
        if not isinstance(self.focused, OperatorPane):
            return
        if self.depth == "tools" and self.active_tools:
            self.active_tool_index = max(0, self.active_tool_index - 1)
            self.render_tool_list()
        elif self.depth == "recipes" and self.active_tools:
            recipes = self.active_tools[self.active_tool_index].recipes
            if recipes:
                self.active_recipe_index = max(0, self.active_recipe_index - 1)
                self.render_recipes(self.active_tools[self.active_tool_index])

    def action_move_down(self) -> None:
        if isinstance(self.focused, Input):
            if self.focused.id == "command-input":
                self.command_history_down()
            return
        if not isinstance(self.focused, OperatorPane):
            return
        if self.depth == "tools" and self.active_tools:
            self.active_tool_index = min(len(self.active_tools) - 1, self.active_tool_index + 1)
            self.render_tool_list()
        elif self.depth == "recipes" and self.active_tools:
            recipes = self.active_tools[self.active_tool_index].recipes
            if recipes:
                self.active_recipe_index = min(len(recipes) - 1, self.active_recipe_index + 1)
                self.render_recipes(self.active_tools[self.active_tool_index])

    def command_history_up(self) -> None:
        if not self.command_history:
            return
        self.command_history_index = max(0, self.command_history_index - 1)
        self.query_one("#command-input", Input).value = self.command_history[self.command_history_index]

    def command_history_down(self) -> None:
        if not self.command_history:
            return
        self.command_history_index = min(len(self.command_history), self.command_history_index + 1)
        command_input = self.query_one("#command-input", Input)
        if self.command_history_index >= len(self.command_history):
            command_input.value = ""
        else:
            command_input.value = self.command_history[self.command_history_index]

    def set_active_category(self, index: int) -> None:
        self.active_category_index = index
        items = list(self.query("#category-list > ListItem"))
        for item_index, item in enumerate(items):
            item.set_class(item_index == index, "active")

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.item is None or not event.item.id or self.depth != "category":
            return
        category_list = self.query_one("#category-list", ListView)
        index = category_list.index or 0
        self.set_active_category(index)
        category = event.item.id.removeprefix("category-").upper()
        self.render_category(category)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.item is None or not event.item.id:
            return
        category_list = self.query_one("#category-list", ListView)
        index = category_list.index or 0
        self.set_active_category(index)
        category = event.item.id.removeprefix("category-").upper()
        self.render_category(category)
        self.action_go_deeper()

    def render_category(self, category: str) -> None:
        description = next((desc for name, desc in CATEGORIES if name == category), "FIELD//OS module")
        self.active_tools = self.tools.for_category(category.lower())
        self.active_tool_index = 0
        self.active_recipe_index = 0
        self.query_one("#breadcrumb", Static).update(f"FIELD//OS > {category}")
        self.query_one("#content-title", Static).update(f"{category} // MODULE")
        self.query_one("#content-description", Static).update(description)
        self.render_tool_list()
        self.query_one("#nav-hint", Static).update(
            "RIGHT / ENTER open library // UP/DOWN modules // CTRL+T terminal // / search"
        )

    def render_tool_list(self) -> None:
        pane = self.query_one("#content-body", OperatorPane)
        category = CATEGORIES[self.active_category_index][0]
        self.query_one("#breadcrumb", Static).update(f"FIELD//OS > {category} > LIBRARY")
        if not self.active_tools:
            pane.update("STATUS      READY\nTOOLS       NONE INDEXED YET\n\nModule online. No manifests currently map to this library.")
            return
        lines = [f"LIBRARY      {category}", f"TOOLS        {len(self.active_tools)} INDEXED", ""]
        focused = self.depth == "tools"
        for index, tool in enumerate(self.active_tools):
            marker = ">>" if focused and index == self.active_tool_index else "  "
            state = "INSTALLED" if tool.installed else "AVAILABLE"
            subcategory = (tool.subcategory or "general").upper()
            lines.append(f"{marker} {tool.name:<22} {state:<9} [{tool.priority.upper()}] // {subcategory}")
        if self.depth == "category":
            lines.extend(["", "RIGHT ARROW // ENTER MODULE LIBRARY"])
        pane.update("\n".join(lines))
        self.query_one("#nav-hint", Static).update(
            "UP/DOWN select tool // RIGHT / ENTER details // LEFT modules // CTRL+T terminal"
        )

    def render_tool_detail(self, tool: ToolRecord) -> None:
        category = tool.category.upper()
        flags = []
        if tool.offline:
            flags.append("OFFLINE")
        if tool.authorised_use_only:
            flags.append("AUTHORISED USE")
        if tool.requires_root:
            flags.append("ELEVATED")
        flag_text = " // ".join(flags) if flags else "STANDARD"
        installed = "YES" if tool.installed else "NO"
        command = tool.command or "N/A"
        platforms = ", ".join(tool.platforms) if tool.platforms else "unspecified"
        self.query_one("#breadcrumb", Static).update(f"FIELD//OS > {category} > {tool.name.upper()}")
        self.query_one("#content-title", Static).update(f"{tool.name.upper()} // TOOL")
        self.query_one("#content-description", Static).update(tool.description or "FIELD//OS indexed tool")
        lines = [
            f"ID          {tool.id}",
            f"CATEGORY    {category}",
            f"SUBCATEGORY {(tool.subcategory or 'general').upper()}",
            f"PRIORITY    {tool.priority.upper()}",
            f"INSTALLED   {installed}",
            f"COMMAND     {command}",
            f"PLATFORMS   {platforms}",
            f"MODE        {flag_text}",
            "",
            f"RECIPES     {len(tool.recipes)} INDEXED",
        ]
        if tool.recipes:
            lines.extend(["", "RIGHT / ENTER opens command recipes"])
            first = tool.recipes[0]
            self.set_terminal_example(first.command, f"EXAMPLE // {first.name}")
        else:
            lines.extend(["", "RIGHT / ENTER stages the base command in the terminal"])
            if tool.command:
                self.set_terminal_example(tool.command, "EXAMPLE // BASE COMMAND")
        self.query_one("#content-body", OperatorPane).update("\n".join(lines))
        self.query_one("#nav-hint", Static).update(
            "RIGHT recipes / stage command // LEFT library // CTRL+T terminal"
        )

    def render_recipes(self, tool: ToolRecord) -> None:
        category = tool.category.upper()
        self.query_one("#breadcrumb", Static).update(
            f"FIELD//OS > {category} > {tool.name.upper()} > RECIPES"
        )
        self.query_one("#content-title", Static).update(f"{tool.name.upper()} // COMMAND RECIPES")
        self.query_one("#content-description", Static).update(
            "Select a recipe to stage it in the live terminal; edit before running if required."
        )
        lines = []
        for index, recipe in enumerate(tool.recipes):
            marker = ">>" if index == self.active_recipe_index else "  "
            lines.append(f"{marker} {recipe.name}")
            if index == self.active_recipe_index:
                if recipe.description:
                    lines.append(f"     {recipe.description}")
                lines.append(f"     $ {recipe.command}")
                self.set_terminal_example(recipe.command, f"EXAMPLE // {tool.name} // {recipe.name}")
            lines.append("")
        self.query_one("#content-body", OperatorPane).update("\n".join(lines).rstrip())
        self.query_one("#nav-hint", Static).update(
            "UP/DOWN recipe // RIGHT / ENTER stage in terminal // LEFT tool // CTRL+T terminal"
        )

    def stage_tool_command(self, tool: ToolRecord) -> None:
        if not tool.command:
            self.notify("NO COMMAND DEFINED", title=tool.name, timeout=1.5)
            return
        self.stage_command(tool.command, f"{tool.name} // BASE COMMAND")

    def stage_command(self, command: str, label: str) -> None:
        command_input = self.query_one("#command-input", Input)
        command_input.value = command
        command_input.cursor_position = len(command)
        self.set_terminal_example(command, f"STAGED // {label}")
        command_input.focus()
        self.write_terminal(f"STAGED // {command}")

    def set_terminal_example(self, command: str, label: str) -> None:
        self.query_one("#terminal-example", Static).update(f"{label}\n$ {command}")

    def write_terminal(self, text: str) -> None:
        self.query_one("#terminal-output", RichLog).write(text)

    async def run_command(self, command: str) -> None:
        if self.command_running:
            self.write_terminal("BUSY // another command is still running")
            return
        self.command_running = True
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.write_terminal(f"[{timestamp}] rvn@fieldos $ {command}")
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            assert process.stdout is not None
            while True:
                raw = await process.stdout.readline()
                if not raw:
                    break
                self.write_terminal(raw.decode(errors="replace").rstrip())
            return_code = await process.wait()
            self.write_terminal(f"[exit {return_code}] // command complete")
        except Exception as exc:
            self.write_terminal(f"[terminal error] {exc}")
        finally:
            self.command_running = False

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "command-input":
            command = event.value.strip()
            if not command:
                return
            self.command_history.append(command)
            self.command_history_index = len(self.command_history)
            event.input.value = ""
            asyncio.create_task(self.run_command(command))
            return

        if event.input.id != "search":
            return
        query = event.value.strip()
        if not query:
            self.action_dashboard()
            return
        matches = self.tools.search(query)
        self.query_one("#breadcrumb", Static).update("FIELD//OS > SEARCH")
        self.query_one("#content-title", Static).update(f'SEARCH // "{query.upper()}"')
        self.query_one("#content-description", Static).update(
            f"{len(matches)} result(s) across tools, metadata and command recipes"
        )
        if not matches:
            body = "NO MATCHES\n\nTry a tool name, category, recipe, command or subcategory."
        else:
            lines = []
            for tool in matches[:25]:
                installed = "INSTALLED" if tool.installed else "AVAILABLE"
                lines.append(
                    f"> {tool.name:<22} {tool.category.upper():<10} {installed:<9} [{tool.priority.upper()}]"
                )
            body = "\n".join(lines)
        self.query_one("#content-body", OperatorPane).update(body)
        self.query_one("#nav-hint", Static).update("ESC dashboard // CTRL+T terminal")


if __name__ == "__main__":
    FieldOSApp().run()
