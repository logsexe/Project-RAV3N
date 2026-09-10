from __future__ import annotations

import signal

from textual.binding import Binding
from textual.css.query import NoMatches
from textual.widgets import Input, RichLog

from .app_v15 import FieldOSApp as V15FieldOSApp


class FieldOSApp(V15FieldOSApp):
    """FIELD//OS V1.5 terminal recovery and clipboard controls."""

    # The inherited Ctrl+C binding is non-priority. Replace it so the command
    # Input cannot consume the operator's interrupt while it owns focus.
    BINDINGS = [binding for binding in V15FieldOSApp.BINDINGS if binding.key != "ctrl+c"] + [
        Binding("ctrl+c", "interrupt", "Interrupt", show=False, priority=True),
        Binding("ctrl+l", "terminal_clear", "Clear terminal", show=False, priority=True),
        Binding("ctrl+shift+l", "terminal_reset", "Reset terminal", show=False, priority=True),
        Binding("ctrl+shift+c", "terminal_copy", "Copy terminal", show=False, priority=True),
    ]

    def render_terminal(self) -> None:
        # A command task can be cancelled during Textual/asyncio shutdown after
        # the widget tree has already been removed. In that state rendering is
        # neither useful nor safe.
        try:
            self.query_one("#body")
        except NoMatches:
            return

        super().render_terminal()
        self.set_header(
            f"ROOT://FIELDOS/{self.operations.active.id}/SHELL",
            f"SHELL::{self.terminals.active.name} // {'BUSY' if self.terminals.active.running else 'READY'}",
            f"CWD // {self.terminals.active.cwd}",
            "ENTER RUN  ^C STOP  ^L CLEAR  ^⇧L RESET  ^⇧C COPY  F6 NEW  F7 CLOSE  ESC RETURN",
        )

    def action_interrupt(self) -> None:
        """Send a real interrupt to the active child command."""
        if self.view != "terminal":
            return
        session = self.terminals.active
        process = self.running_processes.get(session.id)
        if process is None or process.returncode is not None:
            session.append("INTERRUPT // NO RUNNING COMMAND")
            self.render_terminal()
            return

        try:
            process.send_signal(signal.SIGINT)
            session.append("INTERRUPT // SIGINT SENT")
        except (ProcessLookupError, PermissionError, NotImplementedError):
            try:
                process.terminate()
                session.append("INTERRUPT // TERMINATE FALLBACK SENT")
            except ProcessLookupError:
                session.append("INTERRUPT // PROCESS ALREADY EXITED")

        self.render_terminal()

    def action_terminal_clear(self) -> None:
        """Clear the visible/current terminal buffer without affecting a running process."""
        if self.view != "terminal":
            return
        session = self.terminals.active
        session.output.clear()
        session.staged_command = ""
        try:
            box = self.query_one("#command", Input)
            box.value = ""
        except Exception:
            pass
        try:
            self.query_one("#terminal-output", RichLog).clear()
        except NoMatches:
            return
        session.append("TERMINAL // BUFFER CLEARED")
        self.render_terminal()

    def action_terminal_reset(self) -> None:
        """Recover the active terminal and terminate its current child process if needed."""
        if self.view != "terminal":
            return
        session = self.terminals.active
        process = self.running_processes.get(session.id)
        if process is not None and process.returncode is None:
            try:
                process.terminate()
            except ProcessLookupError:
                pass
        session.running = False
        session.output.clear()
        session.staged_command = ""
        try:
            session.history_index = len(session.history)
        except AttributeError:
            pass
        try:
            box = self.query_one("#command", Input)
            box.value = ""
        except Exception:
            pass
        try:
            self.query_one("#terminal-output", RichLog).clear()
        except NoMatches:
            return
        session.append("TERMINAL // SESSION RESET")
        self.render_terminal()

    def action_terminal_copy(self) -> None:
        """Copy the active FIELD//OS terminal transcript through Textual's clipboard support."""
        if self.view != "terminal":
            return
        transcript = "\n".join(self.terminals.active.output)
        if not transcript:
            self.notify("TERMINAL // NOTHING TO COPY", title="FIELD//OS", timeout=1.5)
            return
        try:
            self.copy_to_clipboard(transcript)
        except Exception as exc:
            self.notify(f"COPY FAILED // {exc}", title="FIELD//OS", severity="warning", timeout=3.0)
            return
        self.notify("TERMINAL // OUTPUT COPIED", title="FIELD//OS", timeout=1.5)
