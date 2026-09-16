from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from fieldos.hardware.system import AutoTelemetryProvider
from fieldos.operations import OperationSessionManager
from fieldos.playbooks import PlaybookIndex
from fieldos.themes import THEMES, ThemeManager
from fieldos.tools import ToolIndex


class FieldOSCoreTests(unittest.TestCase):
    def test_tool_manifest_loads(self) -> None:
        tools = ToolIndex.load_default()
        self.assertGreater(len(tools.all), 50)
        self.assertEqual(len({tool.id for tool in tools.all}), len(tools.all))
        self.assertTrue(tools.search("nmap"))
        self.assertTrue(tools.search("trivy"))
        self.assertTrue(tools.search("rtl_test"))
        self.assertTrue(tools.search("subfinder"))

    def test_playbook_manifests_load(self) -> None:
        playbooks = PlaybookIndex.load_default()
        self.assertGreater(len(playbooks.all), 15)
        self.assertEqual(len({playbook.id for playbook in playbooks.all}), len(playbooks.all))
        names = {playbook.name for playbook in playbooks.all}
        self.assertIn("Linux IR", names)
        self.assertIn("PCAP Triage", names)
        self.assertIn("RVN-01 Health Check", names)
        self.assertIn("Authorised Web Baseline", names)

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
