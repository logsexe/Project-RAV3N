from __future__ import annotations

import asyncio
import unittest

from fieldos.app_v14 import FieldOSApp
from fieldos.hardware.mock import MockTelemetryProvider


class FieldOSV14OperatorTests(unittest.TestCase):
    def test_dashboard_command_center_and_help_mount_at_target_size(self) -> None:
        async def exercise() -> None:
            app = FieldOSApp()
            app.telemetry_provider = MockTelemetryProvider()
            async with app.run_test(size=(100, 30)) as pilot:
                await pilot.pause()
                self.assertEqual(app.view, "home")

                app.action_command_center()
                await pilot.pause()
                self.assertEqual(app.view, "command-center")

                app.action_back()
                await pilot.pause()
                self.assertEqual(app.view, "home")

                app.action_help()
                await pilot.pause()
                self.assertEqual(app.view, "help")

                app.action_back()
                await pilot.pause()
                self.assertEqual(app.view, "home")

        asyncio.run(exercise())


if __name__ == "__main__":
    unittest.main()
