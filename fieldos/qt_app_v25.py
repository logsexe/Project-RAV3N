from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

from PySide6.QtCore import QProcess
from PySide6.QtWidgets import QApplication

from .qt_app import FieldOSWindow as V24FieldOSWindow, STYLE, _display_summary


class FieldOSWindow(V24FieldOSWindow):
    """V2.5 terminal reliability pass for RVN-01 and desktop development."""

    def run_terminal_command(self) -> None:
        command = self.command_input.text().strip()
        if not command:
            return
        if self.command_process and self.command_process.state() != QProcess.ProcessState.NotRunning:
            self.terminal_output.append("BUSY // stop current command first")
            return

        # Keep every command visually separated from the previous output.
        self.terminal_output.append("")
        self.terminal_output.append(f"rvn@fieldos:{Path.home()} $ {command}")
        self.command_input.clear()

        process = QProcess(self)
        self.command_process = process
        process.setWorkingDirectory(str(Path.home()))
        process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)

        # QProcess inherits the FIELD//OS environment, but GUI sessions on
        # Raspberry Pi OS can have a narrower PATH than an interactive shell.
        env = process.processEnvironment()
        current_path = env.value("PATH") or os.environ.get("PATH", "")
        standard = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
        if not sys.platform.startswith("win"):
            merged = ":".join(dict.fromkeys((current_path + ":" + standard).split(":")))
            env.insert("PATH", merged)
            process.setProcessEnvironment(env)

        process.readyReadStandardOutput.connect(self._terminal_read)
        process.finished.connect(self._terminal_finished)
        process.errorOccurred.connect(self._terminal_error)

        if sys.platform.startswith("win"):
            process.start("powershell.exe", ["-NoProfile", "-Command", command])
        else:
            shell = shutil.which("bash") or "/bin/sh"
            args = ["-lc", command] if shell.endswith("bash") else ["-c", command]
            process.start(shell, args)

    def _terminal_read(self) -> None:
        if not self.command_process:
            return
        text = bytes(self.command_process.readAllStandardOutput()).decode(errors="replace")
        if not text:
            return
        # Preserve program output exactly, while ensuring the completion marker
        # and next prompt cannot be glued to the final output line.
        self.terminal_output.moveCursor(self.terminal_output.textCursor().MoveOperation.End)
        self.terminal_output.insertPlainText(text)
        self.terminal_output.ensureCursorVisible()

    def _terminal_finished(self, exit_code: int, _status) -> None:
        cursor = self.terminal_output.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        if self.terminal_output.toPlainText() and not self.terminal_output.toPlainText().endswith("\n"):
            self.terminal_output.insertPlainText("\n")
        self.terminal_output.append(f"[exit {exit_code}] // command complete")
        self.terminal_output.append("")

    def _terminal_error(self, _error) -> None:
        if self.command_process:
            self.terminal_output.append(f"TERMINAL ERROR // {self.command_process.errorString()}")
            self.terminal_output.append("")

    def _tick(self) -> None:
        from datetime import datetime
        self.top.setText(f"RAVEN // RVN-01     FIELD//OS 2.5 DEV     {datetime.now().strftime('%H:%M:%S')}")


def main() -> int:
    print("FIELD//OS V2.5 DEV // PySide6 startup", flush=True)
    print(_display_summary(), flush=True)
    if sys.platform.startswith("linux") and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        print(
            "FIELD//OS: no graphical display is available in this shell. Run from the RVN-01 desktop session or attach the active display session.",
            file=sys.stderr,
            flush=True,
        )
        return 2
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(STYLE)
    window = FieldOSWindow()
    window.show() if "--windowed" in sys.argv else window.showFullScreen()
    print("FIELD//OS: Qt window created", flush=True)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
