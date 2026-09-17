from __future__ import annotations

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from fieldos.qt_field_app import FieldOSWindow


class NavigationSurfaceTests(unittest.TestCase):
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

    def test_navigation_opens_without_waypoint_ui(self) -> None:
        self.window.open_app("NAVIGATION")
        self.qt_app.processEvents()
        self.assertIn("READY", self.window.footer.text())
        self.assertFalse(hasattr(self.window, "waypoints_list"))
        self.assertFalse(hasattr(self.window, "waypoint_detail"))
        self.assertFalse(hasattr(self.window, "nav_tools_panel"))
        self.assertFalse(hasattr(self.window, "map_store"))
        self.assertFalse(hasattr(self.window.map_canvas, "waypoints"))

    def test_navigation_refresh_gps_and_companion_launch_do_not_crash(self) -> None:
        self.window.open_app("NAVIGATION")
        self.qt_app.processEvents()
        self.window.refresh_module("MAP")
        self.qt_app.processEvents()
        self.window.launch_first_service("MAP")
        self.qt_app.processEvents()
        # No QMapShack service is configured in the test environment, so this
        # just confirms the fail-closed path reports clearly instead of crashing.
        self.assertIn("MAP", self.window.footer.text())


if __name__ == "__main__":
    unittest.main()
