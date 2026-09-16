from __future__ import annotations

import gc
import os
import tempfile
import time
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from fieldos.qt_v3_health_app import FieldOSWindow

# This is the actual class the `fieldos` console script and `python -m fieldos`
# launch (see pyproject.toml / fieldos/__main__.py). It sits three
# _replace_page() layers deep (qt_field_app -> qt_v3_app -> qt_v3_health_app),
# each one retiring the previous tier's "LIBRARY"/"RVN-01" page. A page that
# gets orphaned via QStackedWidget.removeWidget() without a surviving Python
# reference becomes eligible for garbage collection, and PySide6 destroys its
# whole C++ widget tree when that happens - including child labels that
# background timers/futures still expect to update. Every other test file in
# this suite instantiates fieldos.qt_field_app.FieldOSWindow directly, which
# never exercises the further replacements above it - exactly why this
# crashed in real interactive use before anything caught it.


class V3HealthAppEntrypointTests(unittest.TestCase):
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

    def test_retired_pages_survive_garbage_collection(self) -> None:
        for _ in range(5):
            gc.collect()
            self.qt_app.processEvents()
            time.sleep(0.02)

        # Retired widgets from each _replace_page() tier must still be alive.
        self.window.library_status.setText("PROBE")
        self.window.system_status.setText("PROBE")
        self.assertEqual(self.window.library_status.text(), "PROBE")
        self.assertEqual(self.window.system_status.text(), "PROBE")

    def test_survives_real_event_loop_with_live_timers_and_futures(self) -> None:
        # Long enough for the startup LIBRARY probe (zim_files scan) and at
        # least one 3s state_timer tick to actually complete and be handled,
        # matching what a real interactive run experiences.
        deadline = time.time() + 4
        while time.time() < deadline:
            self.qt_app.processEvents()
            time.sleep(0.02)

        self.assertIn("ZIM FILES", self.window.library_status.text())
        self.assertIn("HOST", self.window.system_status.text())

    def test_rvn01_health_dashboard_still_refreshes_after_three_page_swaps(self) -> None:
        self.window.open_app("RVN-01")
        deadline = time.time() + 5
        while time.time() < deadline and "PROBING" in self.window.rvn_panels["SYSTEM"].text():
            self.qt_app.processEvents()
            time.sleep(0.02)
        self.assertNotIn("PROBING", self.window.rvn_panels["SYSTEM"].text())


if __name__ == "__main__":
    unittest.main()
