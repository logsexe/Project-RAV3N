from __future__ import annotations

import asyncio
from dataclasses import dataclass
import time
from typing import Callable

from fieldos.hardware.mock import Telemetry


UNKNOWN_TELEMETRY = Telemetry(
    mesh="UNKNOWN",
    gps="UNKNOWN",
    network="UNKNOWN",
    cpu_temp_c=-1,
    storage_percent=0,
    battery_percent=-1,
)


@dataclass(slots=True, frozen=True)
class HardwareSnapshot:
    telemetry: Telemetry
    updated_at: float = 0.0
    polling: bool = False

    @property
    def age_seconds(self) -> float | None:
        if self.updated_at <= 0:
            return None
        return max(0.0, time.monotonic() - self.updated_at)


class HardwareService:
    """Single non-blocking owner for FIELD//OS hardware telemetry.

    Apps consume the cached snapshot. Only this service calls the physical
    telemetry provider, preventing RADIO/MAP/MESH/SYSTEM screens from each
    blocking the Textual event loop or duplicating hardware probes.
    """

    def __init__(self, provider, on_update: Callable[[Telemetry], None] | None = None) -> None:
        self.provider = provider
        self.on_update = on_update
        self._telemetry = UNKNOWN_TELEMETRY
        self._updated_at = 0.0
        self._polling = False

    @property
    def telemetry(self) -> Telemetry:
        return self._telemetry

    @property
    def snapshot(self) -> HardwareSnapshot:
        return HardwareSnapshot(self._telemetry, self._updated_at, self._polling)

    async def poll(self) -> Telemetry:
        if self._polling:
            return self._telemetry
        self._polling = True
        try:
            telemetry = await asyncio.to_thread(self.provider.read)
            self._telemetry = telemetry
            self._updated_at = time.monotonic()
            if self.on_update is not None:
                self.on_update(telemetry)
            return telemetry
        finally:
            self._polling = False
