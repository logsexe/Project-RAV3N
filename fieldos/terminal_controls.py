from __future__ import annotations

from textual.widgets import Input, RichLog


def clear_terminal_view(app) -> None:
    """Clear the active terminal transcript buffer and input safely."""
    session = app.terminals.active
    session.output.clear()
    session.staged_command = ""
    session.staged_label = ""
    try:
        session.history_index = len(session.history)
    except AttributeError:
        pass

    try:
        command = app.query_one("#command", Input)
        command.value = ""
    except Exception:
        pass

    try:
        log = app.query_one("#terminal-output", RichLog)
        log.clear()
    except Exception:
        pass

    session.append("TERMINAL // BUFFER CLEARED")
    if app.view == "terminal":
        app.render_terminal()


def reset_terminal_view(app) -> None:
    """Recover an active FIELD//OS terminal without restarting the application."""
    session = app.terminals.active
    process = getattr(app, "running_processes", {}).get(session.id)
    if process is not None and process.returncode is None:
        try:
            process.terminate()
        except ProcessLookupError:
            pass

    session.running = False
    session.output.clear()
    session.staged_command = ""
    session.staged_label = ""
    try:
        session.history_index = len(session.history)
    except AttributeError:
        pass

    try:
        command = app.query_one("#command", Input)
        command.value = ""
    except Exception:
        pass

    try:
        log = app.query_one("#terminal-output", RichLog)
        log.clear()
    except Exception:
        pass

    session.append("TERMINAL // SESSION RESET")
    if app.view == "terminal":
        app.render_terminal()
