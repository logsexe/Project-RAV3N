from __future__ import annotations

import importlib.util
import shutil
from dataclasses import dataclass


@dataclass(frozen=True)
class Service:
    key: str
    label: str
    module: str
    strategy: str
    repo: str
    executables: tuple[str, ...] = ()
    python_modules: tuple[str, ...] = ()

    def detected(self) -> bool:
        return any(shutil.which(name) for name in self.executables) or any(
            importlib.util.find_spec(name) is not None for name in self.python_modules
        )

    def status(self) -> str:
        return "READY" if self.detected() else "NOT INSTALLED"


SERVICES = (
    Service("qmapshack", "QMapShack", "MAP", "WRAP", "Maproom/qmapshack", ("qmapshack",)),
    Service("gpsd", "gpsd", "MAP", "DIRECT", "gpsd/gpsd", ("gpsd", "gpspipe", "cgps")),
    Service("gqrx", "Gqrx", "RADIO", "WRAP", "gqrx-sdr/gqrx", ("gqrx",)),
    Service("sdrpp", "SDR++", "RADIO", "WRAP", "AlexandreRouma/SDRPlusPlus", ("sdrpp", "SDR++")),
    Service("meshtastic", "Meshtastic", "MESH", "DIRECT", "meshtastic/python", ("meshtastic",), ("meshtastic",)),
    Service("kiwix", "Kiwix Tools", "LIBRARY", "DIRECT", "kiwix/kiwix-tools", ("kiwix-serve", "kiwix-search", "kiwix-manage")),
    Service("freetak", "FreeTAKServer", "TAK", "OPTIONAL", "FreeTAKTeam/FreeTakServer", ("freetakserver",), ("FreeTAKServer",)),
    Service("psutil", "psutil", "SYSTEM", "DIRECT", "giampaolo/psutil", python_modules=("psutil",)),
)


def services_for(module: str) -> tuple[Service, ...]:
    return tuple(item for item in SERVICES if item.module == module)


def capability_text(module: str) -> str:
    matches = services_for(module)
    if not matches:
        return "No upstream service registered."
    return "\n".join(f"{item.label:<16} {item.status():<13} {item.strategy}" for item in matches)
