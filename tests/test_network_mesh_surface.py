from __future__ import annotations

import os
import tempfile
import time
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from fieldos.qt_field_app import FieldOSWindow


class NetworkMeshSurfaceTests(unittest.TestCase):
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

    def _drain_futures(self, *keys: str, timeout: float = 5.0) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline and any(key in self.window.futures for key in keys):
            self.qt_app.processEvents()
            time.sleep(0.02)
        self.qt_app.processEvents()

    def test_network_page_lists_interfaces_and_neighbours_without_crashing(self) -> None:
        self.window.open_app("NETWORK")
        self.qt_app.processEvents()
        self.assertGreaterEqual(self.window.network_interfaces_list.count(), 1)
        self.assertGreaterEqual(self.window.network_neighbours_list.count(), 1)
        self.assertIn("HOST", self.window.network_status.text())

    def test_mesh_page_reports_node_state_without_crashing(self) -> None:
        self.window.open_app("MESH")
        self._drain_futures("MESH", "MESHNODES")
        self.assertGreaterEqual(self.window.mesh_nodes_list.count(), 1)
        self.assertIn("LINK", self.window.mesh_status.text())

    def test_navigating_away_and_back_keeps_ops_intact(self) -> None:
        self.window.open_app("NETWORK")
        self.qt_app.processEvents()
        self.window.open_app("MESH")
        self._drain_futures("MESH", "MESHNODES")
        self.window.open_app("OPS")
        self.qt_app.processEvents()
        self.assertIn("OPERATION FIELD-001", self.window.ops_meta.text())


if __name__ == "__main__":
    unittest.main()
