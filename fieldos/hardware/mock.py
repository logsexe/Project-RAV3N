from __future__ import annotations

from dataclasses import dataclass
from random import randint, uniform


@dataclass(slots=True)
class Telemetry:
    mesh: str
    gps: str
    network: str
    cpu_temp_c: float
    storage_percent: int
    battery_percent: int


class MockTelemetryProvider:
    """Development telemetry used before RVN-01 hardware is online."""

    def read(self) -> Telemetry:
        return Telemetry(
            mesh="NOT PRESENT",
            gps="NOT PRESENT",
            network="DEV",
            cpu_temp_c=round(uniform(38.0, 49.0), 1),
            storage_percent=randint(18, 24),
            battery_percent=randint(76, 82),
        )
