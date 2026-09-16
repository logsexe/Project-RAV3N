from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from fieldos.map_radio_adapters import discover_mbtiles, rtl_fft
from fieldos.qt_map_radio_app import FieldOSWindow


class MapRadioAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.qt_app = QApplication.instance() or QApplication([])

    def test_adapter_shell_builds(self) -> None:
        window = FieldOSWindow()
        window.resize(800, 480)
        self.qt_app.processEvents()
        self.assertTrue(hasattr(window, "map_canvas"))
        self.assertTrue(hasattr(window, "spectrum_canvas"))
        window.close()

    def test_mbtiles_discovery_returns_list(self) -> None:
        self.assertIsInstance(discover_mbtiles(), list)

    def test_rtl_fft_fails_closed_without_requirements(self) -> None:
        result = rtl_fft(100_000_000, sample_count=1024)
        self.assertIsInstance(result, list)


if __name__ == "__main__":
    unittest.main()
