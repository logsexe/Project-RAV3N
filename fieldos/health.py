from __future__ import annotations

import platform
import shutil
import sys
from pathlib import Path

from fieldos.hardware.system import AutoTelemetryProvider
from fieldos.knowledge import KnowledgeIndex
from fieldos.playbooks import PlaybookIndex
from fieldos.tools import ToolIndex


def main() -> None:
    tools = ToolIndex.load_default()
    knowledge = KnowledgeIndex.load_default()
    playbooks = PlaybookIndex.load_default()
    telemetry = AutoTelemetryProvider()
    details = telemetry.details()
    current = telemetry.read()

    print("RAVEN // FIELD//OS V1.0 // HEALTH CHECK")
    print(f"Python       {sys.version.split()[0]}")
    print(f"Platform     {platform.platform()}")
    print(f"Machine      {platform.machine()}")
    print(f"Hostname     {details.hostname}")
    print(f"Tools        {len(tools.all)} indexed / {tools.installed_count()} detected")
    print(f"Knowledge    {len(knowledge.all)} entries")
    print(f"Playbooks    {len(playbooks.all)}")
    print(f"Network      {current.network}")
    print(f"GPS          {current.gps}")
    print(f"Mesh         {current.mesh}")
    print(f"CPU temp     {'unknown' if current.cpu_temp_c < 0 else f'{current.cpu_temp_c:.1f} C'}")
    print(f"Storage      {current.storage_percent}% used")
    print(f"Battery      {'external/unknown' if current.battery_percent < 0 else f'{current.battery_percent}%'}")

    print("\nOPTIONAL RVN-01 COMMANDS")
    for command in ("gpspipe", "meshtastic", "nmap", "tcpdump", "tshark", "rtl_433", "git"):
        print(f"{command:<12} {'READY' if shutil.which(command) else 'NOT INSTALLED'}")

    data_root = Path.home() / ".fieldos"
    print(f"\nData root    {data_root}")
    print("RESULT       FIELD//OS CORE READY")


if __name__ == "__main__":
    main()
