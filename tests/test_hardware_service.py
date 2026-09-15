from __future__ import annotations

import unittest

from fieldos.core.hardware_service import HardwareService
from fieldos.hardware.mock import Telemetry


class Provider:
    def __init__(self) -> None:
        self.calls = 0

    def read(self) -> Telemetry:
        self.calls += 1
        return Telemetry(
            mesh="CLI READY",
            gps="NO FIX",
            network="WLAN0",
            cpu_temp_c=44.0,
            storage_percent=20,
            battery_percent=-1,
        )


class HardwareServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_starts_unknown_and_caches_poll_result(self) -> None:
        provider = Provider()
        service = HardwareService(provider)
        self.assertEqual(service.telemetry.network, "UNKNOWN")
        self.assertEqual(provider.calls, 0)

        telemetry = await service.poll()

        self.assertEqual(provider.calls, 1)
        self.assertEqual(telemetry.network, "WLAN0")
        self.assertEqual(service.telemetry.mesh, "CLI READY")
        self.assertIsNotNone(service.snapshot.age_seconds)


if __name__ == "__main__":
    unittest.main()
