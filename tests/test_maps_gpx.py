from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fieldos.maps import OfflineMapStore


class GpxExportImportTests(unittest.TestCase):
    def test_export_writes_a_gpx_file_with_all_waypoints(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = OfflineMapStore(Path(tmp) / "maps")
            store.add_waypoint(-37.8136, 144.9631, "Base Camp", "FIELD-001")
            store.add_waypoint(-37.8200, 144.9700, "Overwatch", "FIELD-001")

            archive = store.export_gpx()

            self.assertTrue(archive.exists())
            content = archive.read_text(encoding="utf-8")
            self.assertIn("Base Camp", content)
            self.assertIn("Overwatch", content)
            self.assertIn('lat="-37.8136"', content)

    def test_export_to_explicit_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = OfflineMapStore(Path(tmp) / "maps")
            store.add_waypoint(1.0, 2.0, "Point A")
            target = Path(tmp) / "custom.gpx"

            result = store.export_gpx(target)

            self.assertEqual(result, target)
            self.assertTrue(target.exists())

    def test_import_round_trips_through_export(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            source = OfflineMapStore(Path(tmp) / "source-maps")
            source.add_waypoint(-37.8136, 144.9631, "Base Camp", "FIELD-001")
            archive = source.export_gpx()

            destination = OfflineMapStore(Path(tmp) / "dest-maps")
            imported = destination.import_gpx(archive, "FIELD-002")

            self.assertEqual(len(imported), 1)
            self.assertEqual(imported[0].label, "Base Camp")
            self.assertAlmostEqual(imported[0].latitude, -37.8136)
            self.assertAlmostEqual(imported[0].longitude, 144.9631)
            self.assertEqual(imported[0].operation_id, "FIELD-002")

            stored = destination.waypoints()
            self.assertEqual(len(stored), 1)
            self.assertEqual(stored[0].id, "WP-0001")

    def test_import_from_third_party_gpx_without_project_conventions(self) -> None:
        # A GPX file that never went through export_gpx() - no <comment>,
        # no particular id scheme - to confirm import doesn't assume its own
        # export format on the way back in.
        gpx_text = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="SomeOtherTool">
  <wpt lat="51.5074" lon="-0.1278">
    <name>London Marker</name>
  </wpt>
  <wpt lat="48.8566" lon="2.3522">
    <name>Paris Marker</name>
  </wpt>
</gpx>
"""
        with tempfile.TemporaryDirectory() as tmp:
            gpx_path = Path(tmp) / "external.gpx"
            gpx_path.write_text(gpx_text, encoding="utf-8")
            store = OfflineMapStore(Path(tmp) / "maps")

            imported = store.import_gpx(gpx_path)

            self.assertEqual(len(imported), 2)
            labels = {item.label for item in imported}
            self.assertEqual(labels, {"London Marker", "Paris Marker"})

    def test_import_unnamed_waypoint_gets_a_placeholder_label(self) -> None:
        gpx_text = """<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1"><wpt lat="1.0" lon="2.0"></wpt></gpx>
"""
        with tempfile.TemporaryDirectory() as tmp:
            gpx_path = Path(tmp) / "unnamed.gpx"
            gpx_path.write_text(gpx_text, encoding="utf-8")
            store = OfflineMapStore(Path(tmp) / "maps")

            imported = store.import_gpx(gpx_path)

            self.assertEqual(len(imported), 1)
            self.assertEqual(imported[0].label, "WAYPOINT")


if __name__ == "__main__":
    unittest.main()
