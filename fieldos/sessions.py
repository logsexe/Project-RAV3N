from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import os


@dataclass(slots=True)
class TerminalSession:
    """Independent FIELD//OS terminal workspace."""

    id: str
    name: str
    cwd: str = field(default_factory=os.getcwd)
    tool_id: str | None = None
    tool_name: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    output: list[str] = field(default_factory=list)
    history: list[str] = field(default_factory=list)
    history_index: int = 0
    running: bool = False
    staged_command: str = ""
    staged_label: str = ""

    def append(self, line: str) -> None:
        self.output.append(line)
        if len(self.output) > 1000:
            del self.output[:-1000]

    def push_history(self, command: str) -> None:
        self.history.append(command)
        if len(self.history) > 250:
            del self.history[:-250]
        self.history_index = len(self.history)


class TerminalSessionManager:
    """Owns multiple independent terminal buffers and histories."""

    def __init__(self) -> None:
        self._sessions: list[TerminalSession] = []
        self._counter = 0
        self.active_index = -1
        self.create("SHELL-01")

    @property
    def sessions(self) -> tuple[TerminalSession, ...]:
        return tuple(self._sessions)

    @property
    def active(self) -> TerminalSession:
        return self._sessions[self.active_index]

    def create(self, name: str | None = None, *, tool_id: str | None = None, tool_name: str | None = None) -> TerminalSession:
        self._counter += 1
        session = TerminalSession(
            id=f"TERM-{self._counter:02d}",
            name=name or f"SHELL-{self._counter:02d}",
            tool_id=tool_id,
            tool_name=tool_name,
        )
        session.append("FIELD//OS LOCAL SHELL ONLINE")
        session.append(f"SESSION // {session.name}")
        session.append(f"CWD // {session.cwd}")
        self._sessions.append(session)
        self.active_index = len(self._sessions) - 1
        return session

    def create_for_tool(self, tool_id: str, tool_name: str) -> TerminalSession:
        base = "".join(char for char in tool_name.upper() if char.isalnum())[:10] or "TOOL"
        existing = sum(1 for item in self._sessions if item.tool_id == tool_id)
        return self.create(f"{base}-{existing + 1:02d}", tool_id=tool_id, tool_name=tool_name)

    def next(self) -> TerminalSession:
        self.active_index = (self.active_index + 1) % len(self._sessions)
        return self.active

    def previous(self) -> TerminalSession:
        self.active_index = (self.active_index - 1) % len(self._sessions)
        return self.active

    def close_active(self) -> TerminalSession:
        if len(self._sessions) == 1:
            current = self.active
            current.output.clear()
            current.history.clear()
            current.history_index = 0
            current.staged_command = ""
            current.staged_label = ""
            current.append("FIELD//OS LOCAL SHELL ONLINE")
            current.append(f"SESSION // {current.name}")
            current.append(f"CWD // {current.cwd}")
            return current

        self._sessions.pop(self.active_index)
        self.active_index = min(self.active_index, len(self._sessions) - 1)
        return self.active
