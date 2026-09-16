from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from fieldos.qt_field_app import FieldOSWindow


class NavigationWaypointsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.qt_app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._prev_data_dir = os.environ.get("FIELDOS_DATA_DIR")
        os.environ["FIELDOS_DATA_DIR"] = self._tmp.name
        self.window = FieldOSWindow()
        self.qt_app.processEvents()
        self.window.open_app("NAVIGATION")
        self.qt_app.processEvents()

    def tearDown(self) -> None:
        self.window.close()
        self.qt_app.processEvents()
        if self._prev_data_dir is None:
            os.environ.pop("FIELDOS_DATA_DIR", None)
        else:
            os.environ["FIELDOS_DATA_DIR"] = self._prev_data_dir
        self._tmp.cleanup()

    def test_navigation_opens_with_no_waypoints(self) -> None:
        self.assertEqual(self.window.waypoints_list.count(), 0)
        self.assertEqual(self.window.waypoint_detail.text(), "SELECT A WAYPOINT")

    def test_add_waypoint_is_rejected_without_a_gps_fix(self) -> None:
        self.window._add_waypoint()
        self.assertEqual(self.window.waypoints_list.count(), 0)
        self.assertIn("NO GPS FIX", self.window.footer.text())

    def test_add_waypoint_with_fix_updates_list_canvas_and_timeline(self) -> None:
        self.window.map_canvas.set_fix(-37.8136, 144.9631, 45.0, "FIX")
        with patch("fieldos.qt_field_app.QInputDialog.getText", return_value=("Base Camp", True)):
            self.window._add_waypoint()

        self.assertEqual(self.window.waypoints_list.count(), 1)
        self.assertIn("Base Camp", self.window.waypoints_list.item(0).text())
        self.assertEqual(len(self.window.map_canvas.waypoints), 1)
        self.assertEqual(self.window.map_canvas.waypoints[0][2], "Base Camp")

        events = self.window.ops_engine.timeline(self.window.operations.active.id)
        self.assertTrue(any(event.event_type == "WAYPOINT" for event in events))

    def test_add_waypoint_declined_dialog_adds_nothing(self) -> None:
        self.window.map_canvas.set_fix(-37.8136, 144.9631, 0.0, "FIX")
        with patch("fieldos.qt_field_app.QInputDialog.getText", return_value=("", False)):
            self.window._add_waypoint()
        self.assertEqual(self.window.waypoints_list.count(), 0)

    def test_selecting_waypoint_shows_range_from_current_fix(self) -> None:
        self.window.map_store.add_waypoint(-37.8200, 144.9700, "Second Point", self.window.operations.active.id)
        self.window._refresh_waypoints()
        self.window.map_canvas.set_fix(-37.8136, 144.9631, 0.0, "FIX")

        self.window.waypoints_list.setCurrentRow(0)
        self.qt_app.processEvents()
        self.assertIn("Second Point", self.window.waypoint_detail.text())
        self.assertIn("FROM CURRENT FIX", self.window.waypoint_detail.text())

    def test_selecting_waypoint_without_fix_reports_range_unavailable(self) -> None:
        self.window.map_store.add_waypoint(-37.8200, 144.9700, "No Fix Point", self.window.operations.active.id)
        self.window._refresh_waypoints()
        self.window.waypoints_list.setCurrentRow(0)
        self.qt_app.processEvents()
        self.assertIn("RANGE UNAVAILABLE", self.window.waypoint_detail.text())

    def test_waypoints_persist_across_navigation(self) -> None:
        self.window.map_canvas.set_fix(-37.8136, 144.9631, 0.0, "FIX")
        with patch("fieldos.qt_field_app.QInputDialog.getText", return_value=("Persist Point", True)):
            self.window._add_waypoint()

        self.window.open_app("OPS")
        self.qt_app.processEvents()
        self.window.open_app("NAVIGATION")
        self.qt_app.processEvents()
        self.assertEqual(self.window.waypoints_list.count(), 1)

    def test_export_gpx_with_no_waypoints_is_rejected(self) -> None:
        self.window._export_waypoints_gpx()
        self.assertIn("NO WAYPOINTS", self.window.footer.text())

    def test_export_gpx_writes_a_file_and_reports_success(self) -> None:
        self.window.map_canvas.set_fix(-37.8136, 144.9631, 0.0, "FIX")
        with patch("fieldos.qt_field_app.QInputDialog.getText", return_value=("Base Camp", True)):
            self.window._add_waypoint()

        self.window._export_waypoints_gpx()

        self.assertIn("GPX EXPORTED", self.window.footer.text())
        exports = self.window.map_store.root / "exports"
        gpx_files = list(exports.glob("*.gpx"))
        self.assertEqual(len(gpx_files), 1)
        self.assertIn("Base Camp", gpx_files[0].read_text(encoding="utf-8"))

    def test_import_gpx_cancelled_dialog_adds_nothing(self) -> None:
        with patch("fieldos.qt_field_app.QFileDialog.getOpenFileName", return_value=("", "")):
            self.window._import_waypoints_gpx()
        self.assertEqual(self.window.waypoints_list.count(), 0)

    def test_import_gpx_adds_waypoints_and_records_ops_events(self) -> None:
        gpx_text = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<gpx version="1.1"><wpt lat="10.0" lon="20.0"><name>Imported Point</name></wpt></gpx>\n'
        )
        gpx_path = Path(self._tmp.name) / "incoming.gpx"
        gpx_path.write_text(gpx_text, encoding="utf-8")

        with patch("fieldos.qt_field_app.QFileDialog.getOpenFileName", return_value=(str(gpx_path), "GPX files (*.gpx)")):
            self.window._import_waypoints_gpx()

        self.assertEqual(self.window.waypoints_list.count(), 1)
        self.assertIn("Imported Point", self.window.waypoints_list.item(0).text())
        self.assertIn("IMPORTED 1 WAYPOINT", self.window.footer.text())

        events = self.window.ops_engine.timeline(self.window.operations.active.id)
        self.assertTrue(any(event.event_type == "WAYPOINT" for event in events))

    def test_import_gpx_bad_file_reports_failure_without_crashing(self) -> None:
        bad_path = Path(self._tmp.name) / "not-gpx.txt"
        bad_path.write_text("this is not xml at all {}", encoding="utf-8")

        with patch("fieldos.qt_field_app.QFileDialog.getOpenFileName", return_value=(str(bad_path), "")):
            self.window._import_waypoints_gpx()

        self.assertIn("GPX IMPORT FAILED", self.window.footer.text())
        self.assertEqual(self.window.waypoints_list.count(), 0)


if __name__ == "__main__":
    unittest.main()
