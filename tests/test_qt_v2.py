from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from fieldos.qt_app import APPS, FieldOSWindow


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
        self.assertEqual(len(APPS), 9)
        self.assertEqual(len(self.window.buttons), 9)
        self.assertIs(self.window.stack.currentWidget(), self.window.launcher)

    def test_every_primary_app_opens_and_returns(self) -> None:
        for name, _ in APPS:
            with self.subTest(name=name):
                self.window.open_app(name)
                self.qt_app.processEvents()
                self.assertIs(self.window.stack.currentWidget(), self.window.pages[name])
                self.window.show_launcher()
                self.qt_app.processEvents()
                self.assertIs(self.window.stack.currentWidget(), self.window.launcher)

    def test_window_resizes_to_target_geometry(self) -> None:
        self.window.resize(800, 480)
        self.qt_app.processEvents()
        self.assertEqual(self.window.size().width(), 800)
        self.assertEqual(self.window.size().height(), 480)


if __name__ == "__main__":
    unittest.main()
