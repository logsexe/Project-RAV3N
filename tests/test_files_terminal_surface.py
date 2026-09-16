from __future__ import annotations

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

from fieldos.qt_field_app import FieldOSWindow


class FilesTerminalSurfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.qt_app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._prev_data_dir = os.environ.get("FIELDOS_DATA_DIR")
        os.environ["FIELDOS_DATA_DIR"] = self._tmp.name
        self.window = FieldOSWindow()
        self.qt_app.processEvents()

    def tearDown(self) -> None:
        self.window.close()
        self.qt_app.processEvents()
        if self._prev_data_dir is None:
            os.environ.pop("FIELDOS_DATA_DIR", None)
        else:
            os.environ["FIELDOS_DATA_DIR"] = self._prev_data_dir
        self._tmp.cleanup()

    def _run_command(self, command: str, timeout: float = 10.0) -> None:
        self.window.command_input.setText(command)
        self.window.run_terminal_command()
        deadline = time.time() + timeout
        while time.time() < deadline and self.window.command_process is not None and self.window.command_process.state() != self.window.command_process.ProcessState.NotRunning:
            self.qt_app.processEvents()
            time.sleep(0.02)
        self.qt_app.processEvents()

    def test_files_opens_on_home_directory(self) -> None:
        self.window.open_app("FILES")
        self.qt_app.processEvents()
        self.assertEqual(self.window.files_current_dir, Path.home())
        self.assertEqual(self.window.files_path_label.text(), str(Path.home()))

    def test_files_navigates_into_and_up_from_a_subdirectory(self) -> None:
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            child = root / "child"
            child.mkdir()
            (child / "note.txt").write_text("hi", encoding="utf-8")

            self.window._files_navigate(root)
            self.assertEqual(self.window.files_current_dir, root)
            self.assertEqual(self.window.files_list.count(), 1)
            self.assertTrue(self.window.files_list.item(0).text().startswith("[DIR]"))

            self.window._open_files_entry(self.window.files_list.item(0))
            self.assertEqual(self.window.files_current_dir, child)
            self.assertEqual(self.window.files_list.count(), 1)

            self.window._files_go_up()
            self.assertEqual(self.window.files_current_dir, root)

    def test_files_operation_folder_button_navigates_to_active_session(self) -> None:
        self.window._files_navigate(self.window.operations.session_path())
        self.assertEqual(self.window.files_current_dir, self.window.operations.session_path())
        entries = {self.window.files_list.item(i).text() for i in range(self.window.files_list.count())}
        # OperationSessionManager always provisions these six subdirectories
        # plus its own metadata.json at the session root.
        for expected_dir in ("notes", "commands", "scans", "captures", "evidence", "exports"):
            self.assertIn(f"[DIR]  {expected_dir}", entries)
        self.assertTrue(any("metadata.json" in item for item in entries))

    def test_terminal_command_output_is_captured_into_active_operation(self) -> None:
        self.window.open_app("TERMINAL")
        self._run_command("echo HELLO_FIELD_OS")

        self.assertIn("HELLO_FIELD_OS", self.window.terminal_output.toPlainText())
        self.assertIn("[exit", self.window.terminal_output.toPlainText())
        self.assertIn("CAPTURED", self.window.footer.text())

        commands_dir = self.window.operations.session_path() / "commands"
        captured = list(commands_dir.glob("*.txt"))
        self.assertEqual(len(captured), 1)
        content = captured[0].read_text(encoding="utf-8")
        self.assertIn("COMMAND: echo HELLO_FIELD_OS", content)
        self.assertIn("HELLO_FIELD_OS", content)

    def test_terminal_history_recall_with_up_arrow(self) -> None:
        self.window.open_app("TERMINAL")
        self._run_command("echo FIRST")
        self._run_command("echo SECOND")
        self.assertEqual(self.window.terminal_history, ["echo FIRST", "echo SECOND"])

        self.window.command_input.clear()
        up = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Up, Qt.KeyboardModifier.NoModifier)
        self.window.eventFilter(self.window.command_input, up)
        self.assertEqual(self.window.command_input.text(), "echo SECOND")

        self.window.eventFilter(self.window.command_input, up)
        self.assertEqual(self.window.command_input.text(), "echo FIRST")

        down = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Down, Qt.KeyboardModifier.NoModifier)
        self.window.eventFilter(self.window.command_input, down)
        self.assertEqual(self.window.command_input.text(), "echo SECOND")

    def test_terminal_cd_changes_working_directory_without_spawning_a_process(self) -> None:
        self.window.open_app("TERMINAL")
        with tempfile.TemporaryDirectory() as scratch:
            self.window.command_input.setText(f"cd {scratch}")
            self.window.run_terminal_command()
            self.qt_app.processEvents()
            self.assertEqual(str(self.window.terminal_cwd), str(Path(scratch).resolve()))
            self.assertIsNone(self.window.command_process)

    def test_terminal_cd_to_missing_directory_reports_error_and_keeps_cwd(self) -> None:
        self.window.open_app("TERMINAL")
        original_cwd = self.window.terminal_cwd
        self.window.command_input.setText("cd /definitely/not/a/real/path/xyz")
        self.window.run_terminal_command()
        self.qt_app.processEvents()
        self.assertEqual(self.window.terminal_cwd, original_cwd)
        self.assertIn("no such directory", self.window.terminal_output.toPlainText())


if __name__ == "__main__":
    unittest.main()
