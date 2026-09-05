from __future__ import annotations

import asyncio
from pathlib import Path

from textual.binding import Binding
from textual.widgets import Input, RichLog, Static

from fieldos.app_v05 import FieldOSApp as BaseFieldOSApp, OperatorPane
from fieldos.hardware.system import AutoTelemetryProvider
from fieldos.themes import ThemeManager


class FieldOSApp(BaseFieldOSApp):
    """FIELD//OS V1.0 production-ready software baseline for RVN-01."""

    BINDINGS = [
        Binding("up", "move_up", show=False), Binding("down", "move_down", show=False),
        Binding("right", "open", show=False), Binding("enter", "open", show=False),
        Binding("left", "back", show=False), Binding("escape", "back", show=False),
        Binding("/", "search", show=False), Binding("f1", "help", "Help"),
        Binding("f2", "terminal", "Terminal"), Binding("f3", "sessions", "Sessions"),
        Binding("f4", "status", "Status"), Binding("f5", "notes", "Notes"),
        Binding("f9", "playbooks", "Playbooks"), Binding("f10", "theme", "Theme"),
        Binding("ctrl+c", "interrupt", "Interrupt", show=False), Binding("ctrl+q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.telemetry_provider = AutoTelemetryProvider()
        self.themes = ThemeManager()
        self.running_processes: dict[str, asyncio.subprocess.Process] = {}

    def on_mount(self) -> None:
        super().on_mount()
        self.apply_theme()

    def refresh_status(self) -> None:
        t = self.telemetry_provider.read()

        def dot(value: object, letter: str) -> str:
            return f"{letter}○" if str(value).upper() in {"OFF", "NOT PRESENT", "DISCONNECTED", "UNKNOWN"} else f"{letter}●"

        battery = "EXT" if t.battery_percent < 0 else f"{t.battery_percent}%"
        self.query_one("#status", Static).update(
            f"RAVEN // {self.operations.active.id:<14}        {dot(t.mesh,'M')} {dot(t.gps,'G')} {dot(t.network,'N')} BAT {battery}"
        )

    def action_status(self) -> None:
        if self.view != "status":
            self.return_view = self.view
        self.view = "status"
        self.hide_aux()
        t = self.telemetry_provider.read()
        d = self.telemetry_provider.details()
        battery = "EXTERNAL / UNKNOWN" if t.battery_percent < 0 else f"{t.battery_percent}%"
        temp = "UNKNOWN" if t.cpu_temp_c < 0 else f"{t.cpu_temp_c:.1f} C"
        interfaces = ", ".join(d.interfaces) if d.interfaces else "NONE"
        self.query_one("#body", OperatorPane).update(
            f"OPERATION   {self.operations.active.id}\n"
            f"HOSTNAME    {d.hostname}\n"
            f"PLATFORM    {d.platform}\n"
            f"NETWORK     {t.network}\n"
            f"INTERFACES  {interfaces}\n"
            f"GPS         {t.gps}\n"
            f"MESH        {t.mesh}\n"
            f"CPU TEMP    {temp}\n"
            f"STORAGE     {t.storage_percent}%\n"
            f"BATTERY     {battery}\n"
            f"TERMINALS   {len(self.terminals.sessions)}\n"
            f"KNOWLEDGE   {len(self.knowledge.all)}\n"
            f"THEME       {self.themes.current.name}"
        )
        self.set_header("FIELD//OS > STATUS", "RVN-01 // SYSTEM STATUS", "Live platform and hardware readiness", "ESC BACK  F2 TERMINAL  F10 THEME")
        self.focus_body()

    def action_help(self) -> None:
        if self.view != "help":
            self.return_view = self.view
        self.view = "help"
        self.hide_aux()
        self.query_one("#body", OperatorPane).update(
            "↑ ↓        Navigate\n→ / ENTER  Open / select\n← / ESC    Back\n/          Global search\n"
            "K          Offline knowledge\nF          Favourites / toggle in tool\nR          Recent tools\n"
            "F2         Terminal\nF3         Operations\nF4         System status\nF5         Notes\n"
            "F9         Playbooks\nF10        Cycle theme\nCTRL+Q     Quit\n\nTERMINAL\n"
            "TAB        Next terminal\nSHIFT+TAB  Previous terminal\nF6         New terminal\n"
            "F7         Close terminal\nF8         Clear terminal\nCTRL+C     Interrupt running command\n\n"
            "Every completed command is captured under the active operation."
        )
        self.set_header("FIELD//OS > HELP", "KEYBOARD CONTROL", "RVN-01 compact operator controls", "ESC BACK")
        self.focus_body()

    def action_theme(self) -> None:
        theme = self.themes.next()
        self.apply_theme()
        self.notify(f"THEME // {theme.name}", title="FIELD//OS", timeout=1.5)
        if self.view == "status":
            self.action_status()

    def apply_theme(self) -> None:
        theme = self.themes.current
        self.screen.styles.background = theme.background
        self.screen.styles.color = theme.text
        for selector in ("#status", "#footer"):
            widget = self.query_one(selector, Static)
            widget.styles.background = theme.panel
            widget.styles.color = theme.accent
        for selector in ("#breadcrumb", "#description", "#example"):
            self.query_one(selector, Static).styles.color = theme.muted
        self.query_one("#title", Static).styles.color = theme.text
        body = self.query_one("#body", OperatorPane)
        body.styles.background = theme.panel
        body.styles.color = theme.text
        body.styles.border = ("solid", theme.border)
        for selector in ("#search", "#entry", "#command"):
            box = self.query_one(selector, Input)
            box.styles.background = theme.panel
            box.styles.color = theme.text
            box.styles.border = ("tall", theme.border)
        log = self.query_one("#terminal-output", RichLog)
        log.styles.background = theme.background
        log.styles.color = theme.text

    def action_interrupt(self) -> None:
        if self.view != "terminal":
            return
        session = self.terminals.active
        process = self.running_processes.get(session.id)
        if process and process.returncode is None:
            process.terminate()
            session.append("INTERRUPT // terminate requested")
            if self.view == "terminal":
                self.render_terminal()

    async def run_command(self, command: str, session) -> None:
        if session.running:
            session.append("BUSY // command already running")
            self.render_terminal()
            return

        stripped = command.strip()
        if stripped == "cd" or stripped.startswith("cd "):
            target = stripped[2:].strip().strip('"') or str(Path.home())
            new_path = Path(target).expanduser()
            if not new_path.is_absolute():
                new_path = Path(session.cwd) / new_path
            try:
                resolved = new_path.resolve()
                if not resolved.is_dir():
                    raise NotADirectoryError(str(resolved))
                session.cwd = str(resolved)
                session.append(f"CWD // {session.cwd}")
                self.operations.capture_command(command, [f"CWD // {session.cwd}"], 0, session.name)
            except OSError as exc:
                session.append(f"cd: {exc}")
                self.operations.capture_command(command, [f"cd: {exc}"], 1, session.name)
            if session is self.terminals.active and self.view == "terminal":
                self.render_terminal()
            return

        session.running = True
        session.append(f"rvn@fieldos $ {command}")
        captured: list[str] = []
        exit_code: int | None = None
        if session is self.terminals.active and self.view == "terminal":
            self.render_terminal()
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=session.cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            self.running_processes[session.id] = process
            assert process.stdout is not None
            while True:
                raw = await process.stdout.readline()
                if not raw:
                    break
                line = raw.decode(errors="replace").rstrip()
                captured.append(line)
                session.append(line)
                if session is self.terminals.active and self.view == "terminal":
                    self.query_one("#terminal-output", RichLog).write(line)
            exit_code = await process.wait()
            session.append(f"[exit {exit_code}] // command complete")
        except Exception as exc:
            captured.append(f"[terminal error] {exc}")
            session.append(captured[-1])
        finally:
            self.running_processes.pop(session.id, None)
            session.running = False
            transcript = self.operations.capture_command(command, captured, exit_code, session.name)
            session.append(f"CAPTURED // {transcript.name}")
            if session is self.terminals.active and self.view == "terminal":
                self.render_terminal()
