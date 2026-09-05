from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from fieldos.hardware.system import AutoTelemetryProvider
from fieldos.operations import OperationSessionManager
from fieldos.themes import THEMES, ThemeManager
from fieldos.tools import ToolIndex


class FieldOSCoreTests(unittest.TestCase):
    def test_tool_manifest_loads(self) -> None:
        tools = ToolIndex.load_default()
        self.assertGreater(len(tools.all), 10)
        self.assertTrue(tools.search("nmap"))

    def test_operation_command_capture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manager = OperationSessionManager(Path(tmp) / "sessions")
            path = manager.capture_command("echo hello", ["hello"], 0, "SHELL-01")
            self.assertTrue(path.exists())
            text = path.read_text(encoding="utf-8")
            self.assertIn("COMMAND: echo hello", text)
            self.assertIn("hello", text)
            self.assertIn("commands", str(path))

    def test_theme_cycle(self) -> None:
        manager = ThemeManager()
        first = manager.current
        for _ in range(len(THEMES)):
            manager.next()
        self.assertEqual(manager.current, first)

    def test_telemetry_is_safe_without_hardware(self) -> None:
        telemetry = AutoTelemetryProvider().read()
        self.assertIsInstance(telemetry.network, str)
        self.assertIsInstance(telemetry.gps, str)
        self.assertIsInstance(telemetry.mesh, str)
        self.assertGreaterEqual(telemetry.storage_percent, 0)


if __name__ == "__main__":
    unittest.main()
