from __future__ import annotations

import asyncio
from datetime import datetime

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Input, RichLog, Static

from fieldos.hardware.mock import MockTelemetryProvider
from fieldos.knowledge import KnowledgeEntry, KnowledgeIndex
from fieldos.operations import OperationSessionManager
from fieldos.playbooks import PlaybookIndex
from fieldos.sessions import TerminalSessionManager
from fieldos.state import OperatorState
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
    """FIELD//OS V0.5 compact 800x480 operator environment."""

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
        Binding("up", "move_up", show=False), Binding("down", "move_down", show=False),
        Binding("right", "open", show=False), Binding("enter", "open", show=False),
        Binding("left", "back", show=False), Binding("escape", "back", show=False),
        Binding("/", "search", show=False), Binding("f1", "help", "Help"),
        Binding("f2", "terminal", "Terminal"), Binding("f3", "sessions", "Sessions"),
        Binding("f4", "status", "Status"), Binding("f5", "notes", "Notes"),
        Binding("f9", "playbooks", "Playbooks"), Binding("q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.telemetry_provider = MockTelemetryProvider()
        self.tools = ToolIndex.load_default()
        self.knowledge = KnowledgeIndex.load_default()
        self.state = OperatorState()
        self.terminals = TerminalSessionManager()
        self.operations = OperationSessionManager()
        self.playbooks = PlaybookIndex.load_default()
        self.view = "home"
        self.return_view = "home"
        self.entry_mode: str | None = None
        self.category_index = self.tool_index = self.recipe_index = 0
        self.operation_index = self.operations.active_index
        self.playbook_index = self.playbook_step_index = 0
        self.collection_index = self.knowledge_index = self.search_index = 0
        self.active_tools: list[ToolRecord] = []
        self.collection_tools: list[ToolRecord] = []
        self.search_results: list[tuple[str, ToolRecord | KnowledgeEntry]] = []
        self.active_knowledge: KnowledgeEntry | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="shell"):
            yield Static("RAVEN // FIELD//OS V0.5.0", id="status")
            yield Static("FIELD//OS", id="breadcrumb")
            yield Static("RAVEN", id="title")
            yield Static("FIELD OPERATIONS TERMINAL", id="description")
            yield Input(placeholder="SEARCH", id="search", classes="hidden")
            yield Input(placeholder="ENTRY", id="entry", classes="hidden")
            yield Static("", id="terminal-tabs", classes="hidden")
            yield OperatorPane("", id="body")
            yield Static("", id="example", classes="hidden")
            yield RichLog(id="terminal-output", wrap=True, markup=False, classes="hidden")
            yield Input(placeholder="rvn@fieldos $", id="command", classes="hidden")
            yield Static("", id="footer")

    def on_mount(self) -> None:
        self.set_interval(1.5, self.refresh_status)
        self.render_home(); self.refresh_status(); self.focus_body()

    def focus_body(self) -> None:
        self.query_one("#body", OperatorPane).focus()

    def refresh_status(self) -> None:
        t = self.telemetry_provider.read()
        def dot(value: object, letter: str) -> str:
            return f"{letter}○" if str(value).upper() in {"OFF", "NOT PRESENT", "DISCONNECTED"} else f"{letter}●"
        self.query_one("#status", Static).update(
            f"RAVEN // {self.operations.active.id:<14}        {dot(t.mesh,'M')} {dot(t.gps,'G')} {dot(t.network,'N')} BAT {t.battery_percent}%"
        )

    def hide_aux(self) -> None:
        for selector in ("#search", "#entry", "#terminal-tabs", "#example", "#terminal-output", "#command"):
            self.query_one(selector).add_class("hidden")
        self.query_one("#body").remove_class("hidden")
        self.entry_mode = None

    def set_header(self, breadcrumb: str, title: str, description: str, footer: str) -> None:
        self.query_one("#breadcrumb", Static).update(breadcrumb)
        self.query_one("#title", Static).update(title)
        self.query_one("#description", Static).update(description)
        self.query_one("#footer", Static).update(footer)

    def render_home(self) -> None:
        self.view = "home"; self.hide_aux()
        lines = []
        for i, (name, desc) in enumerate(CATEGORIES):
            marker = ">" if i == self.category_index else " "
            lines.append(f"{marker} {name:<12} {desc:<34} {len(self.tools.for_category(name.lower())):02d}")
        self.query_one("#body", OperatorPane).update("\n".join(lines))
        self.set_header("FIELD//OS > HOME", "MODULES", f"ACTIVE // {self.operations.active.id} // {self.operations.active.name}",
                        "↑↓ SELECT  → OPEN  / SEARCH  K KNOWLEDGE  F FAV  R RECENT  F2 TERM  F3 SESS")

    def render_library(self) -> None:
        self.view = "library"; self.hide_aux()
        category, desc = CATEGORIES[self.category_index]
        self.active_tools = self.tools.for_category(category.lower())
        self.tool_index = min(self.tool_index, max(0, len(self.active_tools)-1))
        lines = []
        for i, tool in enumerate(self.active_tools):
            marker = ">" if i == self.tool_index else " "
            fav = "★" if self.state.is_favourite(tool.id) else " "
            lines.append(f"{marker}{fav} {tool.name:<23} {'INST' if tool.installed else '----'}  {(tool.subcategory or 'general').upper()}")
        self.query_one("#body", OperatorPane).update("\n".join(lines) if lines else "NO TOOLS INDEXED")
        self.set_header(f"FIELD//OS > {category}", f"{category} // LIBRARY", desc,
                        "← BACK  ↑↓ SELECT  → OPEN  / SEARCH  F2 TERMINAL")

    def render_tool(self) -> None:
        if not self.active_tools: return
        self.view = "tool"; self.hide_aux()
        tool = self.active_tools[self.tool_index]
        self.state.record_recent(tool.id)
        fav = "YES" if self.state.is_favourite(tool.id) else "NO"
        lines = [
            f"STATUS       {'INSTALLED' if tool.installed else 'AVAILABLE'}",
            f"FAVOURITE    {fav}", f"COMMAND      {tool.command or 'N/A'}",
            f"PRIORITY     {tool.priority.upper()}",
            f"MODE         {'AUTHORISED USE' if tool.authorised_use_only else 'STANDARD'}", "",
        ]
        if tool.recipes:
            lines.append("RECIPES")
            for i, recipe in enumerate(tool.recipes): lines.append(f"{'>' if i == self.recipe_index else ' '} {recipe.name}")
        else: lines.append("> BASE / CUSTOM COMMAND")
        self.query_one("#body", OperatorPane).update("\n".join(lines))
        self.set_header(f"FIELD//OS > {tool.category.upper()} > {tool.name.upper()}", tool.name.upper(),
                        tool.description or "FIELD//OS indexed tool", "← BACK  ↑↓ RECIPE  → STAGE  F TOGGLE FAV  F2 TERMINAL")

    def tool_by_id(self, tool_id: str) -> ToolRecord | None:
        return next((tool for tool in self.tools.all if tool.id == tool_id), None)

    def render_collection(self, kind: str) -> None:
        self.view = kind; self.hide_aux()
        ids = self.state.favourites if kind == "favourites" else self.state.recent_tools
        self.collection_tools = [tool for item in ids if (tool := self.tool_by_id(item))]
        self.collection_index = min(self.collection_index, max(0, len(self.collection_tools)-1))
        title = "FAVOURITE TOOLS" if kind == "favourites" else "RECENT TOOLS"
        lines = [f"{'>' if i == self.collection_index else ' '} {tool.name:<24} {tool.category.upper():<10} {'INST' if tool.installed else '----'}"
                 for i, tool in enumerate(self.collection_tools)]
        self.query_one("#body", OperatorPane).update("\n".join(lines) if lines else f"NO {title} YET")
        self.set_header(f"FIELD//OS > {title}", title, f"{len(self.collection_tools)} indexed shortcuts", "ESC BACK  ↑↓ SELECT  ENTER OPEN")

    def render_knowledge(self) -> None:
        self.view = "knowledge"; self.hide_aux()
        items = self.knowledge.all
        self.knowledge_index = min(self.knowledge_index, max(0, len(items)-1))
        lines = [f"{'>' if i == self.knowledge_index else ' '} {item.title[:34]:<34} {item.category.upper():<10} {item.source[:12]}"
                 for i, item in enumerate(items[:80])]
        self.query_one("#body", OperatorPane).update("\n".join(lines) if lines else "NO KNOWLEDGE INDEXED")
        self.set_header("FIELD//OS > KNOWLEDGE", "OFFLINE KNOWLEDGE", f"{len(items)} entries // bundled + local sources", "ESC BACK  ↑↓ SELECT  ENTER OPEN  / SEARCH")

    def render_knowledge_entry(self, item: KnowledgeEntry) -> None:
        self.view = "knowledge-detail"; self.hide_aux(); self.active_knowledge = item
        body = [f"SOURCE      {item.source}", f"CATEGORY    {item.category.upper()}"]
        if item.path: body.append(f"PATH        {item.path}")
        if item.command: body.extend(["", "COMMAND", f"$ {item.command}"])
        text = item.body.strip() or item.summary
        if text: body.extend(["", text[:5000]])
        self.query_one("#body", OperatorPane).update("\n".join(body))
        footer = "ESC BACK  ENTER STAGE COMMAND" if item.command else "ESC BACK"
        self.set_header("FIELD//OS > KNOWLEDGE > ENTRY", item.title.upper(), item.summary, footer)

    def action_search(self) -> None:
        if self.view == "terminal": return
        self.return_view = self.view; self.view = "search"; self.hide_aux(); self.search_index = 0
        box = self.query_one("#search", Input); box.value = ""; box.remove_class("hidden"); box.focus()
        self.query_one("#body", OperatorPane).update("TYPE QUERY ABOVE // ENTER SEARCH")
        self.set_header("FIELD//OS > SEARCH", "GLOBAL SEARCH", "Tools, recipes, commands and offline knowledge", "ENTER SEARCH  ESC BACK")

    def render_search_results(self, query: str) -> None:
        tool_matches = self.tools.search(query)
        knowledge_matches = self.knowledge.search(query)
        self.search_results = [("tool", item) for item in tool_matches[:20]] + [("knowledge", item) for item in knowledge_matches[:20]]
        self.search_index = min(self.search_index, max(0, len(self.search_results)-1))
        lines = []
        for i, (kind, item) in enumerate(self.search_results):
            marker = ">" if i == self.search_index else " "
            if kind == "tool": lines.append(f"{marker} TOOL  {item.name:<28} {item.category.upper()}")
            else: lines.append(f"{marker} KNOW  {item.title[:28]:<28} {item.category.upper()}")
        self.query_one("#body", OperatorPane).update("\n".join(lines) if lines else "NO MATCHES")
        self.set_header("FIELD//OS > SEARCH", f'SEARCH // "{query.upper()}"', f"{len(self.search_results)} combined result(s)", "↑↓ SELECT  ENTER OPEN  ESC BACK")
        self.focus_body()

    def action_sessions(self) -> None:
        if self.view != "sessions": self.return_view = self.view
        self.view = "sessions"; self.hide_aux(); self.operation_index = min(self.operation_index, len(self.operations.sessions)-1)
        lines = [f"{'>' if i == self.operation_index else ' '} {item.id:<18} {item.name:<26} {'ACTIVE' if i == self.operations.active_index else ''}"
                 for i, item in enumerate(self.operations.sessions)]
        lines.extend(["", f"DATA // {self.operations.root}"])
        self.query_one("#body", OperatorPane).update("\n".join(lines))
        self.set_header("FIELD//OS > OPERATIONS", "FIELD SESSIONS", "Persistent cases / exercises / field operations", "ESC BACK  ↑↓ SELECT  ENTER ACTIVATE  N NEW  E EXPORT")
        self.focus_body()

    def action_notes(self) -> None:
        if self.view != "notes": self.return_view = self.view
        self.view = "notes"; self.hide_aux(); op = self.operations.active
        self.query_one("#body", OperatorPane).update("\n".join(op.notes[-14:]) if op.notes else "NO NOTES YET\n\nPress N to add a timestamped operation note.")
        self.set_header(f"FIELD//OS > {op.id} > NOTES", "OPERATION NOTES", f"{op.name} // {len(op.notes)} timeline entries", "ESC BACK  N NEW NOTE  F3 SESSIONS  F2 TERMINAL")
        self.focus_body()

    def action_playbooks(self) -> None:
        if self.view not in {"playbooks", "playbook"}: self.return_view = self.view
        self.view = "playbooks"; self.hide_aux(); items = self.playbooks.all
        self.playbook_index = min(self.playbook_index, max(0, len(items)-1))
        lines = [f"{'>' if i == self.playbook_index else ' '} {p.name:<24} {p.category.upper():<10} {len(p.steps):02d} STEPS" for i,p in enumerate(items)]
        self.query_one("#body", OperatorPane).update("\n".join(lines) if lines else "NO PLAYBOOKS INDEXED")
        self.set_header("FIELD//OS > PLAYBOOKS", "OPERATOR PLAYBOOKS", "Guided review-first field workflows", "ESC BACK  ↑↓ SELECT  ENTER OPEN")
        self.focus_body()

    def render_playbook(self) -> None:
        items = self.playbooks.all
        if not items: return
        self.view = "playbook"; self.hide_aux(); p = items[self.playbook_index]
        self.playbook_step_index = min(self.playbook_step_index, max(0, len(p.steps)-1))
        lines = []
        for i, step in enumerate(p.steps):
            lines.append(f"{'>' if i == self.playbook_step_index else ' '} {i+1:02d} // {step.name}")
            if i == self.playbook_step_index:
                if step.description: lines.append(f"     {step.description}")
                if step.command: lines.append(f"     $ {step.command}")
            lines.append("")
        self.query_one("#body", OperatorPane).update("\n".join(lines).rstrip())
        self.set_header(f"FIELD//OS > PLAYBOOKS > {p.name.upper()}", p.name.upper(), p.description, "ESC BACK  ↑↓ STEP  ENTER STAGE / NOTE")
        self.focus_body()

    def action_status(self) -> None:
        if self.view != "status": self.return_view = self.view
        self.view = "status"; self.hide_aux(); t = self.telemetry_provider.read()
        self.query_one("#body", OperatorPane).update(
            f"OPERATION  {self.operations.active.id}\nMESH       {t.mesh}\nGPS        {t.gps}\nNETWORK    {t.network}\nCPU TEMP   {t.cpu_temp_c:.1f} C\nSTORAGE    {t.storage_percent}%\nBATTERY    {t.battery_percent}%\nTERMINALS  {len(self.terminals.sessions)}\nKNOWLEDGE  {len(self.knowledge.all)}\nFAVOURITES {len(self.state.favourites)}")
        self.set_header("FIELD//OS > STATUS", "RVN-01 // STATUS", "Platform telemetry and local indexes", "ESC BACK  F2 TERMINAL  F3 SESSIONS")
        self.focus_body()

    def action_help(self) -> None:
        if self.view != "help": self.return_view = self.view
        self.view = "help"; self.hide_aux()
        self.query_one("#body", OperatorPane).update(
            "↑ ↓        Navigate\n→ / ENTER  Open / select\n← / ESC    Back\n/          Global search\nK          Offline knowledge\nF          Favourites / toggle in tool\nR          Recent tools\nF2         Terminal\nF3         Operations\nF4         Status\nF5         Notes\nF9         Playbooks\n\nTERMINAL\nTAB/SHIFT+TAB switch\nF6 new  F7 close  F8 clear")
        self.set_header("FIELD//OS > HELP", "KEYBOARD CONTROL", "Compact RVN-01 controls", "ESC BACK")
        self.focus_body()

    def render_terminal(self) -> None:
        if self.view != "terminal": self.return_view = self.view
        self.view = "terminal"; self.query_one("#body").add_class("hidden")
        self.query_one("#search").add_class("hidden"); self.query_one("#entry").add_class("hidden")
        for selector in ("#terminal-tabs", "#example", "#terminal-output", "#command"): self.query_one(selector).remove_class("hidden")
        s = self.terminals.active
        tabs = [f"{'>' if i == self.terminals.active_index else ' '}[{item.name}{'*' if item.running else ''}]" for i,item in enumerate(self.terminals.sessions)]
        self.query_one("#terminal-tabs", Static).update("  ".join(tabs))
        self.set_header(f"FIELD//OS > {self.operations.active.id} > TERMINAL", f"{s.name} // {'BUSY' if s.running else 'READY'}", f"CWD // {s.cwd}", "ESC BACK  TAB NEXT  SHIFT+TAB PREV  F6 NEW  F7 CLOSE  F8 CLEAR")
        self.query_one("#example", Static).update(f"{s.staged_label or 'CUSTOM COMMANDS ENABLED'}\n$ {s.staged_command or 'Type any local shell command below'}")
        log = self.query_one("#terminal-output", RichLog); log.clear()
        for line in s.output: log.write(line)
        box = self.query_one("#command", Input); box.value = s.staged_command; box.cursor_position = len(box.value); box.focus()

    def action_terminal(self) -> None: self.render_terminal()

    def action_move_up(self) -> None:
        if self.view == "home": self.category_index = max(0,self.category_index-1); self.render_home()
        elif self.view == "library" and self.active_tools: self.tool_index=max(0,self.tool_index-1); self.render_library()
        elif self.view == "tool" and self.active_tools and self.active_tools[self.tool_index].recipes: self.recipe_index=max(0,self.recipe_index-1); self.render_tool()
        elif self.view in {"favourites","recent"} and self.collection_tools: self.collection_index=max(0,self.collection_index-1); self.render_collection(self.view)
        elif self.view == "knowledge" and self.knowledge.all: self.knowledge_index=max(0,self.knowledge_index-1); self.render_knowledge()
        elif self.view == "search" and self.search_results: self.search_index=max(0,self.search_index-1); self.render_search_results(self.query_one("#search",Input).value)
        elif self.view == "sessions": self.operation_index=max(0,self.operation_index-1); self.action_sessions()
        elif self.view == "playbooks": self.playbook_index=max(0,self.playbook_index-1); self.action_playbooks()
        elif self.view == "playbook": self.playbook_step_index=max(0,self.playbook_step_index-1); self.render_playbook()
        elif self.view == "terminal": self.history_up()

    def action_move_down(self) -> None:
        if self.view == "home": self.category_index=min(len(CATEGORIES)-1,self.category_index+1); self.render_home()
        elif self.view == "library" and self.active_tools: self.tool_index=min(len(self.active_tools)-1,self.tool_index+1); self.render_library()
        elif self.view == "tool" and self.active_tools and self.active_tools[self.tool_index].recipes:
            self.recipe_index=min(len(self.active_tools[self.tool_index].recipes)-1,self.recipe_index+1); self.render_tool()
        elif self.view in {"favourites","recent"} and self.collection_tools: self.collection_index=min(len(self.collection_tools)-1,self.collection_index+1); self.render_collection(self.view)
        elif self.view == "knowledge" and self.knowledge.all: self.knowledge_index=min(len(self.knowledge.all)-1,self.knowledge_index+1); self.render_knowledge()
        elif self.view == "search" and self.search_results: self.search_index=min(len(self.search_results)-1,self.search_index+1); self.render_search_results(self.query_one("#search",Input).value)
        elif self.view == "sessions": self.operation_index=min(len(self.operations.sessions)-1,self.operation_index+1); self.action_sessions()
        elif self.view == "playbooks": self.playbook_index=min(len(self.playbooks.all)-1,self.playbook_index+1); self.action_playbooks()
        elif self.view == "playbook": self.playbook_step_index=min(len(self.playbooks.all[self.playbook_index].steps)-1,self.playbook_step_index+1); self.render_playbook()
        elif self.view == "terminal": self.history_down()

    def open_tool(self, tool: ToolRecord) -> None:
        cat = next((i for i,(name,_) in enumerate(CATEGORIES) if name.lower()==tool.category.lower()),0)
        self.category_index=cat; self.active_tools=self.tools.for_category(tool.category); self.tool_index=next((i for i,t in enumerate(self.active_tools) if t.id==tool.id),0); self.recipe_index=0; self.render_tool()

    def action_open(self) -> None:
        if isinstance(self.focused, Input): return
        if self.view == "home": self.tool_index=0; self.render_library()
        elif self.view == "library" and self.active_tools: self.recipe_index=0; self.render_tool()
        elif self.view == "tool" and self.active_tools:
            tool=self.active_tools[self.tool_index]
            if tool.recipes:
                r=tool.recipes[self.recipe_index]; self.stage_command(r.command,f"EXAMPLE // {tool.name} // {r.name}",tool)
            elif tool.command: self.stage_command(tool.command,f"EXAMPLE // {tool.name} // BASE COMMAND",tool)
        elif self.view in {"favourites","recent"} and self.collection_tools: self.open_tool(self.collection_tools[self.collection_index])
        elif self.view == "knowledge" and self.knowledge.all: self.render_knowledge_entry(self.knowledge.all[self.knowledge_index])
        elif self.view == "knowledge-detail" and self.active_knowledge and self.active_knowledge.command: self.stage_command(self.active_knowledge.command,f"KNOWLEDGE // {self.active_knowledge.title}")
        elif self.view == "search" and self.search_results:
            kind,item=self.search_results[self.search_index]
            if kind=="tool": self.open_tool(item)
            else: self.render_knowledge_entry(item)
        elif self.view == "sessions": self.operations.select(self.operation_index); self.refresh_status(); self.action_sessions()
        elif self.view == "playbooks": self.playbook_step_index=0; self.render_playbook()
        elif self.view == "playbook":
            p=self.playbooks.all[self.playbook_index]; step=p.steps[self.playbook_step_index]
            if step.command: self.stage_command(step.command,f"PLAYBOOK // {p.name} // {step.name}")
            else: self.operations.add_note(f"PLAYBOOK STEP // {p.name} // {step.name}"); self.notify("STEP ADDED TO NOTES",title="PLAYBOOK")

    def action_back(self) -> None:
        if isinstance(self.focused, Input): self.restore_view(self.return_view); return
        if self.view == "tool": self.render_library()
        elif self.view == "library": self.render_home()
        elif self.view == "knowledge-detail": self.render_knowledge()
        elif self.view == "playbook": self.action_playbooks()
        elif self.view in {"terminal","search","status","help","sessions","notes","playbooks","favourites","recent","knowledge"}: self.restore_view(self.return_view)

    def restore_view(self, view: str) -> None:
        if view == "tool": self.render_tool()
        elif view == "library": self.render_library()
        elif view == "knowledge": self.render_knowledge()
        elif view in {"favourites","recent"}: self.render_collection(view)
        elif view == "sessions": self.action_sessions()
        elif view == "notes": self.action_notes()
        elif view == "playbooks": self.action_playbooks()
        elif view == "playbook": self.render_playbook()
        else: self.render_home()
        self.focus_body()

    def stage_command(self, command: str, label: str, tool: ToolRecord | None=None) -> None:
        s=self.terminals.active
        if tool and s.tool_id not in {None,tool.id}: s=self.terminals.create_for_tool(tool.id,tool.name)
        elif tool: s.tool_id,s.tool_name=tool.id,tool.name
        s.staged_command,s.staged_label=command,label; self.render_terminal()

    def history_up(self) -> None:
        s=self.terminals.active
        if not s.history: return
        s.history_index=max(0,s.history_index-1); self.query_one("#command",Input).value=s.history[s.history_index]

    def history_down(self) -> None:
        s=self.terminals.active
        if not s.history: return
        s.history_index=min(len(s.history),s.history_index+1); self.query_one("#command",Input).value="" if s.history_index>=len(s.history) else s.history[s.history_index]

    def on_key(self,event) -> None:
        body=isinstance(self.focused,OperatorPane)
        if body and event.key=="k": event.prevent_default(); event.stop(); self.return_view=self.view; self.render_knowledge(); return
        if body and event.key=="f":
            event.prevent_default(); event.stop()
            if self.view=="tool" and self.active_tools:
                enabled=self.state.toggle_favourite(self.active_tools[self.tool_index].id); self.notify("FAVOURITE ADDED" if enabled else "FAVOURITE REMOVED",title="FIELD//OS"); self.render_tool()
            else: self.return_view=self.view; self.render_collection("favourites")
            return
        if body and event.key=="r": event.prevent_default(); event.stop(); self.return_view=self.view; self.render_collection("recent"); return
        if body and self.view=="sessions" and event.key=="n":
            event.prevent_default(); event.stop(); self.entry_mode="new-session"; box=self.query_one("#entry",Input); box.placeholder="NEW SESSION NAME"; box.value=""; box.remove_class("hidden"); box.focus(); return
        if body and self.view=="sessions" and event.key=="e":
            event.prevent_default(); event.stop(); path=self.operations.export_active(); self.notify(f"EXPORTED // {path}",title="OPERATION",timeout=3); return
        if body and self.view=="notes" and event.key=="n":
            event.prevent_default(); event.stop(); self.entry_mode="note"; box=self.query_one("#entry",Input); box.placeholder="ADD TIMESTAMPED NOTE"; box.value=""; box.remove_class("hidden"); box.focus(); return
        if self.view!="terminal" or not self.query_one("#command",Input).has_focus: return
        if event.key=="tab": event.prevent_default(); event.stop(); self.terminals.next(); self.render_terminal()
        elif event.key=="shift+tab": event.prevent_default(); event.stop(); self.terminals.previous(); self.render_terminal()
        elif event.key=="f6": event.prevent_default(); event.stop(); self.terminals.create(); self.render_terminal()
        elif event.key=="f7": event.prevent_default(); event.stop(); self.terminals.close_active(); self.render_terminal()
        elif event.key=="f8": event.prevent_default(); event.stop(); self.terminals.active.output.clear(); self.terminals.active.append("TERMINAL BUFFER CLEARED"); self.render_terminal()

    def on_input_submitted(self,event: Input.Submitted) -> None:
        if event.input.id=="search":
            query=event.value.strip()
            if query: self.render_search_results(query)
            return
        if event.input.id=="entry":
            value=event.value.strip()
            if self.entry_mode=="new-session" and value: self.operations.create(value); self.operation_index=self.operations.active_index; self.refresh_status(); self.action_sessions()
            elif self.entry_mode=="note" and value: self.operations.add_note(value); self.action_notes()
            return
        if event.input.id=="command":
            command=event.value.strip()
            if not command: return
            s=self.terminals.active; s.push_history(command); s.staged_command=""; event.input.value=""; asyncio.create_task(self.run_command(command,s))

    async def run_command(self,command: str,session) -> None:
        if session.running: session.append("BUSY // command already running"); self.render_terminal(); return
        session.running=True; session.append(f"[{datetime.now().strftime('%H:%M:%S')}] rvn@fieldos $ {command}"); self.render_terminal()
        try:
            process=await asyncio.create_subprocess_shell(command,cwd=session.cwd,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.STDOUT)
            assert process.stdout is not None
            while True:
                raw=await process.stdout.readline()
                if not raw: break
                session.append(raw.decode(errors="replace").rstrip())
                if session is self.terminals.active and self.view=="terminal": self.query_one("#terminal-output",RichLog).write(session.output[-1])
            code=await process.wait(); session.append(f"[exit {code}] // command complete")
        except Exception as exc: session.append(f"[terminal error] {exc}")
        finally:
            session.running=False
            if session is self.terminals.active and self.view=="terminal": self.render_terminal()


if __name__ == "__main__":
    FieldOSApp().run()
