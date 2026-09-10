from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
import unittest

from fieldos.app_v13 import FieldOSApp
from fieldos.hardware.mock import MockTelemetryProvider


class FieldOSUISmokeTests(unittest.TestCase):
    def test_v13_mounts_and_primary_navigation_survives(self) -> None:
        async def exercise() -> None:
            with tempfile.TemporaryDirectory() as tmp:
                app = FieldOSApp()
                app.telemetry_provider = MockTelemetryProvider()
                app.operations.root = Path(tmp) / "sessions"

                async with app.run_test(size=(100, 30)) as pilot:
                    await pilot.pause()
                    self.assertEqual(app.view, "home")

                    app.action_terminal()
                    await pilot.pause()
                    self.assertEqual(app.view, "terminal")

                    app.action_back()
                    await pilot.pause()
                    self.assertEqual(app.view, "home")

                    app.action_playbooks()
                    await pilot.pause()
                    self.assertEqual(app.view, "playbooks")

                    if app.playbooks.all:
                        app.action_open()
                        await pilot.pause()
                        self.assertEqual(app.view, "playbook")
                        app.action_back()
                        await pilot.pause()
                        self.assertEqual(app.view, "playbooks")

                    app.action_back()
                    await pilot.pause()
                    self.assertEqual(app.view, "home")

                    app.action_intelligence()
                    await pilot.pause()
                    self.assertEqual(app.view, "intelligence")
                    app.action_back()
                    await pilot.pause()
                    self.assertEqual(app.view, "home")

        asyncio.run(exercise())


if __name__ == "__main__":
    unittest.main()
