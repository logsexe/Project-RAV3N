from __future__ import annotations

import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from fieldos.qt_field_app import FieldOSWindow


class RadioTuningSliderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.qt_app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._prev_data_dir = os.environ.get("FIELDOS_DATA_DIR")
        os.environ["FIELDOS_DATA_DIR"] = self._tmp.name
        self.window = FieldOSWindow()
        self.qt_app.processEvents()
        self.window.open_app("RADIO")
        self.qt_app.processEvents()

    def tearDown(self) -> None:
        self.window.close()
        self.qt_app.processEvents()
        if self._prev_data_dir is None:
            os.environ.pop("FIELDOS_DATA_DIR", None)
        else:
            os.environ["FIELDOS_DATA_DIR"] = self._prev_data_dir
        self._tmp.cleanup()

    def test_slider_defaults_match_the_text_field(self) -> None:
        self.assertEqual(self.window.frequency_slider.value(), 100)
        self.assertEqual(self.window.frequency_input.text(), "100.000")
        self.assertEqual(self.window.frequency_slider.minimum(), self.window.TUNE_SLIDER_MIN_MHZ)
        self.assertEqual(self.window.frequency_slider.maximum(), self.window.TUNE_SLIDER_MAX_MHZ)

    def test_dragging_the_slider_updates_text_and_tunes(self) -> None:
        self.window.frequency_slider.setValue(250)
        self.qt_app.processEvents()
        self.assertEqual(self.window.frequency_input.text(), "250.000")
        self.assertIn("250.000 MHz", self.window.footer.text())
        self.assertIn("RX PREVIEW", self.window.footer.text())
        self.assertEqual(self.window.spectrum_canvas.center_hz, 250_000_000)

    def test_typing_a_precise_value_rounds_the_slider_without_losing_precision(self) -> None:
        self.window.frequency_input.setText("100.300")
        self.window.frequency_input.returnPressed.emit()
        self.qt_app.processEvents()
        self.assertEqual(self.window.frequency_slider.value(), 100)
        self.assertEqual(self.window.frequency_input.text(), "100.300")
        self.assertIn("100.300 MHz", self.window.footer.text())

    def test_invalid_frequency_text_reports_clearly_without_crashing(self) -> None:
        self.window.frequency_input.setText("not-a-number")
        self.window.frequency_input.returnPressed.emit()
        self.qt_app.processEvents()
        self.assertIn("INVALID FREQUENCY", self.window.footer.text())

    def test_out_of_range_frequency_is_rejected(self) -> None:
        self.window.frequency_input.setText("5000")
        self.window.frequency_input.returnPressed.emit()
        self.qt_app.processEvents()
        self.assertIn("OUT OF PREVIEW RANGE", self.window.footer.text())


if __name__ == "__main__":
    unittest.main()
