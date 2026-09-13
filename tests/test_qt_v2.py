from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from fieldos.qt_app import APP_SPECS, FieldOSWindow


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

    def test_launcher_contains_nine_primary_apps(self) -> None:
        self.assertEqual(len(APP_SPECS), 9)
        self.assertEqual(len(self.window.launcher.buttons), 9)
        self.assertIs(self.window.stack.currentWidget(), self.window.launcher)

    def test_every_primary_app_opens_and_returns(self) -> None:
        for spec in APP_SPECS:
            with self.subTest(app_id=spec.app_id):
                self.window.open_app(spec.app_id)
                self.qt_app.processEvents()
                self.assertIs(self.window.stack.currentWidget(), self.window.pages[spec.app_id])
                self.window.show_launcher()
                self.qt_app.processEvents()
                self.assertIs(self.window.stack.currentWidget(), self.window.launcher)

    def test_target_geometry_is_supported(self) -> None:
        self.assertGreaterEqual(self.window.minimumWidth(), 800)
        self.assertGreaterEqual(self.window.minimumHeight(), 480)


if __name__ == "__main__":
    unittest.main()
