from __future__ import annotations

import unittest

from fieldos.app_v15 import FieldOSApp
from fieldos.hardware.mock import MockTelemetryProvider


class FieldOSV15UITests(unittest.IsolatedAsyncioTestCase):
    async def test_tool_center_plugins_and_hardware_are_navigable(self) -> None:
        app = FieldOSApp()
        app.telemetry_provider = MockTelemetryProvider()
        async with app.run_test(size=(100, 30)) as pilot:
            self.assertEqual(app.view, "home")

            app.render_tool_center()
            await pilot.pause()
            self.assertEqual(app.view, "tool-center")

            app.render_plugins()
            await pilot.pause()
            self.assertEqual(app.view, "plugins")
            self.assertGreaterEqual(len(app.plugins.all), 1)

            app.render_plugin_detail()
            await pilot.pause()
            self.assertEqual(app.view, "plugin-detail")

            app.action_back()
            await pilot.pause()
            self.assertEqual(app.view, "plugins")

            app.action_status()
            await pilot.pause()
            self.assertEqual(app.view, "status")

            app.action_back()
            await pilot.pause()
            self.assertEqual(app.view, "home")

    async def test_plugin_toggle_is_operator_controlled(self) -> None:
        app = FieldOSApp()
        app.telemetry_provider = MockTelemetryProvider()
        async with app.run_test(size=(100, 30)) as pilot:
            app.render_plugins()
            await pilot.pause()
            before = app.plugins.all[0].enabled
            app.action_toggle_plugin()
            await pilot.pause()
            self.assertEqual(app.plugins.all[0].enabled, not before)


if __name__ == "__main__":
    unittest.main()
