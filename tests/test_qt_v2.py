from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from fieldos.live_services import RadioState, gpsd_fix, radio_state, system_metrics, zim_files
from fieldos.qt_app import APPS, FieldOSWindow
from fieldos.service_registry import SERVICES, capability_text


class FieldOSV2QtTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.qt_app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.window = FieldOSWindow()
        self.window.resize(800, 480)
        self.window.show()
        self.qt_app.processEvents()

    def tearDown(self) -> None:
        self.window.close()
        self.qt_app.processEvents()

    def test_home_is_initial_surface(self) -> None:
        self.assertIs(self.window.stack.currentWidget(), self.window.home)
        self.window.show_launcher()
        self.qt_app.processEvents()
        self.assertIs(self.window.stack.currentWidget(), self.window.launcher)

    def test_launcher_contains_ten_primary_apps(self) -> None:
        self.window.show_launcher()
        self.assertEqual(len(APPS), 10)
        self.assertEqual(len(self.window.buttons), 10)
        self.assertIn(("TAK", "Situational awareness"), APPS)

    def test_every_primary_app_opens_and_returns(self) -> None:
        self.window.show_launcher()
        for name, _ in APPS:
            with self.subTest(name=name):
                self.window.open_app(name)
                self.qt_app.processEvents()
                self.assertIs(self.window.stack.currentWidget(), self.window.pages[name])
                self.window.show_launcher()
                self.qt_app.processEvents()
                self.assertIs(self.window.stack.currentWidget(), self.window.launcher)

    def test_service_registry_covers_external_capabilities(self) -> None:
        modules = {service.module for service in SERVICES}
        for module in {"MAP", "RADIO", "MESH", "TAK", "LIBRARY", "SYSTEM"}:
            self.assertIn(module, modules)
            self.assertTrue(capability_text(module))

    def test_live_probe_functions_fail_closed(self) -> None:
        metrics = system_metrics()
        self.assertIn("PSUTIL", metrics)
        self.assertIsInstance(zim_files(), tuple)
        self.assertIsInstance(radio_state(), RadioState)
        self.assertIn(gpsd_fix(timeout=0.01).state, {"GPSD OFFLINE", "NO DATA", "NO FIX", "FIX"})

    def test_about_and_contact_return_home(self) -> None:
        self.window.stack.setCurrentWidget(self.window.about)
        self.window.show_home()
        self.assertIs(self.window.stack.currentWidget(), self.window.home)
        self.window.stack.setCurrentWidget(self.window.contact)
        self.window.show_home()
        self.assertIs(self.window.stack.currentWidget(), self.window.home)

    def test_window_resizes_to_target_geometry(self) -> None:
        self.window.resize(800, 480)
        self.qt_app.processEvents()
        self.assertEqual(self.window.size().width(), 800)
        self.assertEqual(self.window.size().height(), 480)


if __name__ == "__main__":
    unittest.main()
