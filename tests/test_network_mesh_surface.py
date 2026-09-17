from __future__ import annotations

import os
import tempfile
import time
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from fieldos.live_services import WifiNetwork
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

    def test_network_page_reports_monitor_mode_status(self) -> None:
        with patch("fieldos.qt_field_app.monitor_mode_capable", return_value=True):
            self.window.open_app("NETWORK")
            self.qt_app.processEvents()
        self.assertIn("MONITOR MODE   READY", self.window.network_wifi_status.text())

    def test_wifi_panel_is_collapsed_by_default(self) -> None:
        self.window.open_app("NETWORK")
        self.qt_app.processEvents()
        self.assertFalse(self.window.wifi_panel.isVisible())
        self.assertFalse(self.window.wifi_toggle.isChecked())

    def test_wifi_toggle_shows_and_hides_the_panel(self) -> None:
        self.window.show()
        self.window.open_app("NETWORK")
        self.qt_app.processEvents()

        self.window.wifi_toggle.setChecked(True)
        self.qt_app.processEvents()
        self.assertTrue(self.window.wifi_panel.isVisible())
        self.assertIn("v", self.window.wifi_toggle.text())

        self.window.wifi_toggle.setChecked(False)
        self.qt_app.processEvents()
        self.assertFalse(self.window.wifi_panel.isVisible())
        self.assertIn(">", self.window.wifi_toggle.text())

    def test_wifi_scan_is_not_triggered_automatically(self) -> None:
        # Unlike interfaces/neighbours, a Wi-Fi scan sends probe requests and
        # must only ever run on an explicit operator click - never on the
        # periodic refresh_local_state() timer.
        with patch("fieldos.qt_field_app.wifi_scan") as mock_scan:
            self.window.open_app("NETWORK")
            self.qt_app.processEvents()
            self.window.refresh_local_state()
            self.qt_app.processEvents()
        mock_scan.assert_not_called()

    def test_wifi_scan_button_disables_during_scan_and_populates_results(self) -> None:
        networks = (WifiNetwork("HomeNet", "AA:BB:CC:DD:EE:FF", 6, 72, "WPA2"),)
        with patch("fieldos.qt_field_app.wifi_scan", return_value=networks):
            self.window.open_app("NETWORK")
            self.qt_app.processEvents()
            self.window._scan_wifi()
            self.assertFalse(self.window.wifi_scan_button.isEnabled())
            self._drain_futures("WIFISCAN")

        self.assertTrue(self.window.wifi_scan_button.isEnabled())
        self.assertEqual(self.window.network_wifi_list.count(), 1)
        self.assertIn("HomeNet", self.window.network_wifi_list.item(0).text())
        self.assertIn("1 NETWORK(S)", self.window.footer.text())

    def test_wifi_scan_with_no_results_reports_clearly(self) -> None:
        with patch("fieldos.qt_field_app.wifi_scan", return_value=()):
            self.window.open_app("NETWORK")
            self.qt_app.processEvents()
            self.window._scan_wifi()
            self._drain_futures("WIFISCAN")
        self.assertEqual(self.window.network_wifi_list.count(), 1)
        self.assertIn("NO NETWORKS FOUND", self.window.network_wifi_list.item(0).text())

    def test_wifi_scan_clicked_again_while_in_flight_does_not_resubmit(self) -> None:
        with patch("fieldos.qt_field_app.wifi_scan", return_value=()) as mock_scan:
            self.window.open_app("NETWORK")
            self.qt_app.processEvents()
            self.window._scan_wifi()
            self.window._scan_wifi()
            self.window._scan_wifi()
            self._drain_futures("WIFISCAN")
        self.assertEqual(mock_scan.call_count, 1)

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
