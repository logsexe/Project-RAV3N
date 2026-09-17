from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from fieldos.map_radio_adapters import RtlSdrStream, _fft_bins_from_iq, discover_mbtiles, rtl_fft
from fieldos.qt_map_radio_app import FieldOSWindow

HAS_NUMPY = importlib.util.find_spec("numpy") is not None


def _drain_futures(qt_app: QApplication, window: FieldOSWindow, *keys: str, timeout: float = 5.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline and any(key in window.futures for key in keys):
        qt_app.processEvents()
        time.sleep(0.02)
    qt_app.processEvents()


def _fake_rtlsdr_module(sdr_factory) -> types.ModuleType:
    module = types.ModuleType("rtlsdr")
    module.RtlSdr = sdr_factory  # type: ignore[attr-defined]
    return module


def _find_spec_side_effect(missing: set[str]):
    """Build a `importlib.util.find_spec` stand-in scoped to "rtlsdr" and
    "numpy" only -- every other module name deterministically reports
    "not installed" (`None`) rather than falling through to a real spec
    lookup. `RtlSdrStreamGuardTests`/`RtlSdrStreamCaptureTests` only ever
    care about those two names, but `MapRadioAppStreamingWiringTests` pumps
    a real Qt event loop through a real `FieldOSWindow`, where an unrelated
    timer (MESH/LIBRARY/etc.) could incidentally call `find_spec` too;
    patching this module-global (`importlib.util` is one shared module
    object, so this reaches every caller, matching the existing
    `test_live_services.py` pyroute2 test precedent) must not accidentally
    make some other optional dependency look "available" and attempt a real
    import of something that isn't actually installed here.
    """
    known = {"rtlsdr", "numpy"}

    def _side_effect(name: str):
        if name not in known:
            return None
        return None if name in missing else object()

    return _side_effect


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


@unittest.skipUnless(HAS_NUMPY, "numpy not installed in this environment")
class FftBinsFromIqTests(unittest.TestCase):
    """`_fft_bins_from_iq` is the pipeline shared by both `rtl_fft()` (one-shot
    subprocess capture) and `RtlSdrStream` (continuous pyrtlsdr capture) --
    these tests pin down its shape/normalization contract directly, since
    both callers depend on it producing identical output for identical input.
    """

    def test_produces_256_bins_normalized_relative_to_peak(self) -> None:
        import numpy as np

        n = 16384
        t = np.arange(n)
        tone = np.exp(2j * np.pi * 0.15 * t).astype(np.complex128) * 0.5
        bins = _fft_bins_from_iq(tone)
        self.assertEqual(len(bins), 256)
        # The pipeline normalizes by subtracting the peak and a fixed 28.0 dB
        # offset, so the loudest bin always lands at exactly -28.0 regardless
        # of the absolute input amplitude.
        self.assertAlmostEqual(max(bins), -28.0, places=6)

    def test_short_input_fails_closed_to_empty_list(self) -> None:
        import numpy as np

        self.assertEqual(_fft_bins_from_iq(np.zeros(100, dtype=np.complex128)), [])

    def test_custom_bin_count_is_honored(self) -> None:
        import numpy as np

        n = 16384
        samples = (np.random.default_rng(0).standard_normal(n) + 1j * np.random.default_rng(1).standard_normal(n))
        bins = _fft_bins_from_iq(samples, bins=64)
        self.assertEqual(len(bins), 64)


class RtlSdrStreamGuardTests(unittest.TestCase):
    """Failure-mode coverage for `RtlSdrStream.start()` -- every one of these
    fails closed (returns False, `running` stays False) without ever
    touching real pyrtlsdr or hardware, since none of it is available here.
    """

    def test_fails_closed_without_pyrtlsdr_installed(self) -> None:
        with patch(
            "fieldos.map_radio_adapters.importlib.util.find_spec",
            side_effect=_find_spec_side_effect({"rtlsdr"}),
        ):
            stream = RtlSdrStream()
            self.assertFalse(stream.start(100_000_000))
            self.assertFalse(stream.running)

    def test_fails_closed_without_numpy_installed(self) -> None:
        with patch(
            "fieldos.map_radio_adapters.importlib.util.find_spec",
            side_effect=_find_spec_side_effect({"numpy"}),
        ):
            stream = RtlSdrStream()
            self.assertFalse(stream.start(100_000_000))
            self.assertFalse(stream.running)

    def test_fails_closed_when_rtlsdr_import_itself_raises(self) -> None:
        # pyrtlsdr's own rtlsdr/librtlsdr.py loads librtlsdr via ctypes.CDLL
        # at `import rtlsdr` time and raises ImportError right there if the
        # shared library can't be found anywhere -- so a pip-installed
        # pyrtlsdr (a real find_spec hit) can still fail the *import*
        # itself, not just device construction. Setting sys.modules["rtlsdr"]
        # to None is the standard way to force `import rtlsdr` to raise
        # ImportError without needing pyrtlsdr installed to prove it.
        with patch(
            "fieldos.map_radio_adapters.importlib.util.find_spec",
            side_effect=_find_spec_side_effect(set()),
        ), patch.dict(sys.modules, {"rtlsdr": None}):
            stream = RtlSdrStream()
            self.assertFalse(stream.start(100_000_000))
            self.assertFalse(stream.running)

    def test_fails_closed_when_device_construction_raises(self) -> None:
        def raising_sdr(*_args, **_kwargs):
            raise OSError("no RTL-SDR device found")

        fake_module = _fake_rtlsdr_module(raising_sdr)
        with patch(
            "fieldos.map_radio_adapters.importlib.util.find_spec",
            side_effect=_find_spec_side_effect(set()),
        ), patch.dict(sys.modules, {"rtlsdr": fake_module}):
            stream = RtlSdrStream()
            self.assertFalse(stream.start(100_000_000))
            self.assertFalse(stream.running)

    def test_fails_closed_when_configuring_device_raises_and_still_closes_it(self) -> None:
        class FakeSdr:
            def __init__(self) -> None:
                self.closed = False

            @property
            def sample_rate(self):
                return getattr(self, "_sr", None)

            @sample_rate.setter
            def sample_rate(self, value):
                self._sr = value

            @property
            def center_freq(self):
                return getattr(self, "_cf", None)

            @center_freq.setter
            def center_freq(self, _value):
                raise RuntimeError("tuner rejected frequency")

            def close(self) -> None:
                self.closed = True

        instance = FakeSdr()
        fake_module = _fake_rtlsdr_module(MagicMock(return_value=instance))
        with patch(
            "fieldos.map_radio_adapters.importlib.util.find_spec",
            side_effect=_find_spec_side_effect(set()),
        ), patch.dict(sys.modules, {"rtlsdr": fake_module}):
            stream = RtlSdrStream()
            self.assertFalse(stream.start(100_000_000))
            self.assertFalse(stream.running)
        self.assertTrue(instance.closed)

    def test_stop_before_start_is_a_safe_noop(self) -> None:
        stream = RtlSdrStream()
        stream.stop()  # must not raise
        self.assertEqual(stream.snapshot(), [])
        self.assertFalse(stream.running)


@unittest.skipUnless(HAS_NUMPY, "numpy not installed in this environment")
class RtlSdrStreamCaptureTests(unittest.TestCase):
    """Exercises the capture-thread loop end to end against a fake device,
    proving RtlSdrStream's own conversion/publishing/shutdown logic -- not
    pyrtlsdr, which isn't installed or runnable against real hardware here.
    """

    class _FakeSdr:
        def __init__(self) -> None:
            import numpy as np

            self._np = np
            self.sample_rate = None
            self.center_freq = None
            self.gain = None
            self.closed = False
            self.read_calls = 0

        def read_samples(self, num_samples: int):
            self.read_calls += 1
            t = self._np.arange(num_samples)
            return self._np.exp(2j * self._np.pi * 0.2 * t).astype(self._np.complex128) * 0.5

        def close(self) -> None:
            self.closed = True

    def _start_stream_with_fake_device(self, instance) -> RtlSdrStream:
        fake_module = _fake_rtlsdr_module(MagicMock(return_value=instance))
        patcher_spec = patch(
            "fieldos.map_radio_adapters.importlib.util.find_spec",
            side_effect=_find_spec_side_effect(set()),
        )
        patcher_modules = patch.dict(sys.modules, {"rtlsdr": fake_module})
        patcher_spec.start()
        patcher_modules.start()
        self.addCleanup(patcher_spec.stop)
        self.addCleanup(patcher_modules.stop)
        stream = RtlSdrStream(read_size=2048)
        self.addCleanup(stream.stop)
        started = stream.start(100_000_000)
        self.assertTrue(started, "stream failed to start against the fake device")
        return stream

    def test_snapshot_reflects_streamed_bins(self) -> None:
        instance = self._FakeSdr()
        stream = self._start_stream_with_fake_device(instance)
        self.assertTrue(stream.running)

        bins: list[float] = []
        deadline = time.time() + 2.0
        while time.time() < deadline and not bins:
            bins = stream.snapshot()
            time.sleep(0.01)
        self.assertEqual(len(bins), 256)
        self.assertGreater(instance.read_calls, 0)
        self.assertEqual(instance.center_freq, 100_000_000)

    def test_retune_reaches_the_device(self) -> None:
        instance = self._FakeSdr()
        stream = self._start_stream_with_fake_device(instance)
        stream.retune(97_500_000)

        deadline = time.time() + 2.0
        while time.time() < deadline and instance.center_freq != 97_500_000:
            time.sleep(0.01)
        self.assertEqual(instance.center_freq, 97_500_000)

    def test_start_is_idempotent_and_retunes_the_running_stream(self) -> None:
        instance = self._FakeSdr()
        stream = self._start_stream_with_fake_device(instance)
        first_thread = stream._thread

        self.assertTrue(stream.start(88_100_000))
        self.assertIs(stream._thread, first_thread)  # no second thread spawned

        deadline = time.time() + 2.0
        while time.time() < deadline and instance.center_freq != 88_100_000:
            time.sleep(0.01)
        self.assertEqual(instance.center_freq, 88_100_000)

    def test_stop_joins_the_thread_and_closes_the_device(self) -> None:
        instance = self._FakeSdr()
        stream = self._start_stream_with_fake_device(instance)
        stream.stop()
        self.assertFalse(stream.running)
        self.assertTrue(instance.closed)

    def test_device_read_failure_ends_the_thread_and_closes_the_device(self) -> None:
        instance = self._FakeSdr()

        def _break_after_first_read(_n, _orig=instance.read_samples):
            instance.read_calls += 1
            if instance.read_calls > 1:
                raise OSError("device disconnected")
            return _orig(_n)

        instance.read_samples = _break_after_first_read
        stream = self._start_stream_with_fake_device(instance)

        deadline = time.time() + 2.0
        while time.time() < deadline and stream.running:
            time.sleep(0.01)
        self.assertFalse(stream.running)
        self.assertTrue(instance.closed)


class MapRadioAppStreamingWiringTests(unittest.TestCase):
    """`fieldos/qt_map_radio_app.py`'s integration of RtlSdrStream into
    `refresh_live_radio()`/`_collect_futures()`/`closeEvent()` -- covered
    with a fake/mocked RtlSdrStream so this tests FIELD//OS's own wiring,
    not pyrtlsdr.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.qt_app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.window = FieldOSWindow()
        self.qt_app.processEvents()

    def tearDown(self) -> None:
        self.window.rtl_stream = None
        self.window.close()
        self.qt_app.processEvents()

    def test_falls_back_to_one_shot_capture_when_stream_start_fails(self) -> None:
        with patch(
            "fieldos.map_radio_adapters.importlib.util.find_spec",
            side_effect=_find_spec_side_effect({"rtlsdr"}),
        ), patch("fieldos.qt_map_radio_app.rtl_fft", return_value=[-40.0] * 256) as fake_rtl_fft:
            self.window.refresh_live_radio()
            _drain_futures(self.qt_app, self.window, "RTLSTREAM")
            self.assertTrue(self.window._rtl_stream_start_attempted)
            self.assertIsNone(self.window.rtl_stream)

            self.window.refresh_live_radio()
            _drain_futures(self.qt_app, self.window, "RTLFFT")
            fake_rtl_fft.assert_called()
        self.assertEqual(self.window.spectrum_canvas.samples[0], -40.0)
        self.assertIn("SNAPSHOT", self.window.radio_status.text())

    def test_prefers_stream_snapshot_once_stream_is_running(self) -> None:
        fake_stream = MagicMock()
        fake_stream.running = True
        fake_stream.snapshot.return_value = [-12.0] * 256
        self.window.rtl_stream = fake_stream
        self.window._rtl_stream_start_attempted = True

        self.window.refresh_live_radio()
        fake_stream.retune.assert_called_once_with(self.window.spectrum_canvas.center_hz)
        _drain_futures(self.qt_app, self.window, "RTLFFT")

        self.assertEqual(self.window.spectrum_canvas.samples[0], -12.0)
        self.assertIn("STREAM", self.window.radio_status.text())
        self.assertNotIn("RTLSTREAM", self.window.futures)

    def test_does_not_retry_stream_start_after_it_fails_once(self) -> None:
        with patch(
            "fieldos.map_radio_adapters.importlib.util.find_spec",
            side_effect=_find_spec_side_effect({"rtlsdr"}),
        ), patch("fieldos.qt_map_radio_app.rtl_fft", return_value=[]):
            self.window.refresh_live_radio()
            _drain_futures(self.qt_app, self.window, "RTLSTREAM")
            self.assertTrue(self.window._rtl_stream_start_attempted)

        with patch("fieldos.map_radio_adapters.RtlSdrStream.start") as start_spy:
            self.window.refresh_live_radio()
            _drain_futures(self.qt_app, self.window, "RTLFFT")
            start_spy.assert_not_called()

    def test_close_event_stops_an_active_stream(self) -> None:
        fake_stream = MagicMock()
        self.window.rtl_stream = fake_stream
        self.window.close()
        fake_stream.stop.assert_called_once()

    def test_close_event_survives_stream_stop_raising(self) -> None:
        fake_stream = MagicMock()
        fake_stream.stop.side_effect = RuntimeError("device already gone")
        self.window.rtl_stream = fake_stream
        self.window.close()  # must not raise
        fake_stream.stop.assert_called_once()


if __name__ == "__main__":
    unittest.main()
