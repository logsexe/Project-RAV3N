from __future__ import annotations

import unittest

from fieldos.app_v16 import FIELD_APPS, FieldOSApp
from fieldos.hardware.mock import MockTelemetryProvider


class FieldOSV16UITests(unittest.IsolatedAsyncioTestCase):
    async def test_launcher_and_core_apps_mount_at_rvn01_geometry(self) -> None:
        app = FieldOSApp()
        app.telemetry_provider = MockTelemetryProvider()
        async with app.run_test(size=(100, 30)) as pilot:
            self.assertEqual(app.view, "home")
            self.assertEqual(len(FIELD_APPS), 9)

            app.app_index = 0
            app.open_selected_app()
            await pilot.pause()
            self.assertEqual(app.view, "app-radio")
            app.action_back()
            await pilot.pause()
            self.assertEqual(app.view, "home")

            app.app_index = 1
            app.open_selected_app()
            await pilot.pause()
            self.assertEqual(app.view, "app-map")
            app.action_back()

            app.app_index = 2
            app.open_selected_app()
            await pilot.pause()
            self.assertEqual(app.view, "app-mesh")
            app.action_back()

            app.app_index = 3
            app.open_selected_app()
            await pilot.pause()
            self.assertEqual(app.view, "app-network")
            app.action_back()

            app.app_index = 6
            app.open_selected_app()
            await pilot.pause()
            self.assertEqual(app.view, "app-files")
            app.action_back()

            app.app_index = 8
            app.open_selected_app()
            await pilot.pause()
            self.assertEqual(app.view, "status")
            app.action_back()
            await pilot.pause()
            self.assertEqual(app.view, "home")

    async def test_launcher_vertical_navigation_moves_by_app_row(self) -> None:
        app = FieldOSApp()
        app.telemetry_provider = MockTelemetryProvider()
        async with app.run_test(size=(100, 30)) as pilot:
            self.assertEqual(app.app_index, 0)
            app.action_move_down()
            await pilot.pause()
            self.assertEqual(app.app_index, 3)
            app.action_move_down()
            await pilot.pause()
            self.assertEqual(app.app_index, 6)
            app.action_move_up()
            await pilot.pause()
            self.assertEqual(app.app_index, 3)


if __name__ == "__main__":
    unittest.main()
