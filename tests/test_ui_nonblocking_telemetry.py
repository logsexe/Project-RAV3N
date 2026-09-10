from __future__ import annotations

import asyncio
import time
import unittest

from fieldos.app_v14 import FieldOSApp
from fieldos.hardware.mock import Telemetry


class SlowTelemetryProvider:
    def read(self) -> Telemetry:
        time.sleep(0.35)
        return Telemetry(
            mesh="CLI READY",
            gps="NO FIX",
            network="WLAN0",
            cpu_temp_c=48.0,
            storage_percent=25,
            battery_percent=-1,
        )


class NonBlockingTelemetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_app_mounts_and_navigates_while_telemetry_is_slow(self) -> None:
        app = FieldOSApp()
        app.telemetry_provider = SlowTelemetryProvider()

        started = time.perf_counter()
        async with app.run_test(size=(100, 30)) as pilot:
            await pilot.pause()
            mounted_in = time.perf_counter() - started
            self.assertLess(mounted_in, 0.30)

            await pilot.press("f1")
            await pilot.pause()
            self.assertEqual(app.view, "help")

            await pilot.press("escape")
            await pilot.pause()
            self.assertEqual(app.view, "home")

            await asyncio.sleep(0.40)
            self.assertEqual(app._telemetry_snapshot.network, "WLAN0")


if __name__ == "__main__":
    unittest.main()
