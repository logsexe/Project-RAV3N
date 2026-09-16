from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from fieldos.qt_field_app import FieldOSWindow


class OpsSurfaceTests(unittest.TestCase):
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

    def test_ops_opens_on_default_operation_with_zero_counts(self) -> None:
        self.window.open_app("OPS")
        self.qt_app.processEvents()
        self.assertIn("OPERATION FIELD-001", self.window.ops_meta.text())
        self.assertIn("ASSETS 0", self.window.ops_meta.text())
        self.assertIn("EVIDENCE 0", self.window.ops_meta.text())
        self.assertIn("EVENTS 0", self.window.ops_meta.text())

    def test_add_asset_updates_counts_list_and_timeline(self) -> None:
        self.window.open_app("OPS")
        self.window.ops_asset_kind.setText("HOST")
        self.window.ops_asset_value.setText("10.0.0.5")
        self.window.ops_asset_label.setText("GATEWAY")
        self.window._add_ops_asset()

        self.assertIn("ASSETS 1", self.window.ops_meta.text())
        self.assertEqual(self.window.ops_assets.count(), 1)
        self.assertEqual(self.window.ops_assets.item(0).text(), "[HOST] GATEWAY")
        self.assertEqual(self.window.ops_asset_kind.text(), "")
        self.assertEqual(self.window.ops_asset_value.text(), "")

        events = self.window.ops_engine.timeline("FIELD-001")
        self.assertTrue(any(event.event_type == "ASSET" for event in events))

    def test_add_asset_without_kind_or_value_is_rejected(self) -> None:
        self.window.open_app("OPS")
        self.window.ops_asset_kind.setText("")
        self.window.ops_asset_value.setText("")
        self.window._add_ops_asset()
        self.assertEqual(self.window.ops_assets.count(), 0)
        self.assertIn("NEEDS KIND AND VALUE", self.window.footer.text())

    def test_add_note_does_not_affect_asset_evidence_or_event_counts(self) -> None:
        self.window.open_app("OPS")
        self.window.ops_note_input.setText("bench test note")
        self.window._add_ops_note()

        self.assertEqual(self.window.ops_note_input.text(), "")
        self.assertIn("EVENTS 0", self.window.ops_meta.text())
        self.assertIn("bench test note", self.window.operations.active.notes[-1])

    def test_new_operation_switches_to_isolated_state(self) -> None:
        self.window.open_app("OPS")
        self.window.ops_asset_kind.setText("HOST")
        self.window.ops_asset_value.setText("10.0.0.5")
        self.window._add_ops_asset()
        self.assertIn("ASSETS 1", self.window.ops_meta.text())

        self.window.operations.create("SECOND OP")
        self.window._populate_operations()
        self.window._refresh_ops()

        self.assertIn("OPERATION SECOND-OP", self.window.ops_meta.text())
        self.assertIn("ASSETS 0", self.window.ops_meta.text())
        self.assertEqual(self.window.ops_selector.count(), 2)

        self.window._select_operation(0)
        self.assertIn("OPERATION FIELD-001", self.window.ops_meta.text())
        self.assertIn("ASSETS 1", self.window.ops_meta.text())

    def test_export_creates_zip_archive(self) -> None:
        self.window.open_app("OPS")
        self.window._export_operation()
        exports = Path(self._tmp.name) / "exports"
        archives = list(exports.glob("FIELD-001-*.zip"))
        self.assertEqual(len(archives), 1)
        self.assertIn("EXPORTED", self.window.footer.text())


if __name__ == "__main__":
    unittest.main()
