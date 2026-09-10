from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from fieldos.hardware.mock import Telemetry


class SubsystemState(str, Enum):
    READY = "READY"
    DEGRADED = "DEGRADED"
    ABSENT = "ABSENT"
    UNKNOWN = "UNKNOWN"


@dataclass(slots=True, frozen=True)
class SubsystemAssessment:
    name: str
    state: SubsystemState
    detail: str

    @property
    def healthy(self) -> bool:
        return self.state is SubsystemState.READY


@dataclass(slots=True, frozen=True)
class ReadinessAssessment:
    state: str
    subsystems: tuple[SubsystemAssessment, ...]
    advisories: tuple[str, ...]


_DEGRADED_DETAILS = {
    "OFF",
    "DISCONNECTED",
    "NO FIX",
    "NO ADDRESS",
    "LINK LOCAL",
    "LINK UP",
}
_ABSENT_DETAILS = {"NOT PRESENT", "UNSUPPORTED"}
_UNKNOWN_DETAILS = {"UNKNOWN", ""}


def classify(name: str, value: object) -> SubsystemAssessment:
    detail = str(value).strip().upper()
    if detail in _ABSENT_DETAILS:
        state = SubsystemState.ABSENT
    elif detail in _UNKNOWN_DETAILS:
        state = SubsystemState.UNKNOWN
    elif detail in _DEGRADED_DETAILS:
        state = SubsystemState.DEGRADED
    else:
        state = SubsystemState.READY
    return SubsystemAssessment(name=name.upper(), state=state, detail=detail or "UNKNOWN")


def assess_telemetry(telemetry: Telemetry, hot_cpu_c: float = 75.0) -> ReadinessAssessment:
    """Convert raw telemetry into one UI-neutral RVN-01 readiness assessment.

    This module is deliberately read-only. It centralises interpretation only;
    hardware discovery and all operator actions remain elsewhere.
    """
    subsystems = (
        classify("network", telemetry.network),
        classify("gps", telemetry.gps),
        classify("mesh", telemetry.mesh),
    )
    advisories = [f"{item.name} {item.detail}" for item in subsystems if not item.healthy]
    if telemetry.cpu_temp_c >= hot_cpu_c:
        advisories.append(f"CPU HOT {telemetry.cpu_temp_c:.0f}C")
    return ReadinessAssessment(
        state="READY" if not advisories else "DEGRADED",
        subsystems=subsystems,
        advisories=tuple(advisories),
    )
