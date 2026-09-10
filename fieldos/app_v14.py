from __future__ import annotations

import asyncio
from datetime import datetime

from textual.binding import Binding
from textual.widgets import Static

from .app_v13 import FieldOSApp as V13FieldOSApp
from .app_v12 import NAV_ITEMS, OperatorPane
from .hardware.mock import Telemetry


class FieldOSApp(V13FieldOSApp):
    """FIELD//OS V1.4 — finished RVN-01 operator experience."""

    TITLE = "RAVEN // FIELD//OS V1.4"
    BINDINGS = V13FieldOSApp.BINDINGS + [
        Binding("f8", "command_center", "Command Center"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._telemetry_snapshot = Telemetry(
            mesh="UNKNOWN",
            gps="UNKNOWN",
            network="UNKNOWN",
            cpu_temp_c=-1,
            storage_percent=0,
            battery_percent=-1,
        )
        self._telemetry_worker_active = False

    def on_mount(self) -> None:
        # Base mount renders immediately. Real RVN-01 hardware polling is kept
        # off the Textual event loop so slow gpsd/gpspipe checks never freeze
        # startup or keyboard navigation.
        super().on_mount()
        self.run_worker(self._poll_telemetry(), group="telemetry", exclusive=True)
        self.set_interval(3.0, self._schedule_telemetry_poll)

    def _schedule_telemetry_poll(self) -> None:
        if self._telemetry_worker_active:
            return
        self.run_worker(self._poll_telemetry(), group="telemetry", exclusive=True)

    async def _poll_telemetry(self) -> None:
        self._telemetry_worker_active = True
        try:
            self._telemetry_snapshot = await asyncio.to_thread(self.telemetry_provider.read)
        finally:
            self._telemetry_worker_active = False
        self.refresh_status()
        if self.view == "home":
            self.render_home()
        elif self.view == "command-center":
            self.action_command_center()

    @staticmethod
    def _telemetry_flag(value: object) -> str:
        degraded = {
            "OFF",
            "NOT PRESENT",
            "DISCONNECTED",
            "UNKNOWN",
            "NO FIX",
            "NO ADDRESS",
            "LINK LOCAL",
            "LINK UP",
        }
        return "--" if str(value).upper() in degraded else "OK"

    def refresh_status(self) -> None:
        t = self._telemetry_snapshot
        a = self._airgap_state()
        temp = "--" if t.cpu_temp_c < 0 else f"{t.cpu_temp_c:.0f}C"
        clock = datetime.now().strftime("%H:%M")
        self.query_one("#status", Static).update(
            f" RVN-01 | OS 1.4 | OP {self.operations.active.id[:10]:<10} | "
            f"{self.profiles.current.name:<8} | {'ISOLATED' if a.active else 'LINKED':<8} | "
            f"NET {self._telemetry_flag(t.network):<2} GPS {self._telemetry_flag(t.gps):<2} "
            f"MESH {self._telemetry_flag(t.mesh):<2} | {temp:<4} | {clock} "
        )

    def _readiness(self, telemetry: Telemetry | None = None) -> tuple[str, list[str]]:
        t = telemetry or self._telemetry_snapshot
        warnings: list[str] = []
        if self._telemetry_flag(t.network) != "OK":
            warnings.append(f"NETWORK {str(t.network).upper()}")
        if self._telemetry_flag(t.gps) != "OK":
            warnings.append("GPS NO FIX")
        if self._telemetry_flag(t.mesh) != "OK":
            warnings.append("MESH OFFLINE")
        if t.cpu_temp_c >= 75:
            warnings.append(f"CPU HOT {t.cpu_temp_c:.0f}C")
        return ("READY" if not warnings else "DEGRADED", warnings)

    def render_home(self) -> None:
        self.view = "home"
        self.hide_aux()
        t = self._telemetry_snapshot
        a = self._airgap_state()
        op = self.operations.active.id
        assets = len(self.intelligence.list_assets(op))
        evidence = len(self.intelligence.list_evidence(op))
        events = len(self.intelligence.timeline(op, limit=999))
        readiness, warnings = self._readiness(t)
        temp = "--" if t.cpu_temp_c < 0 else f"{t.cpu_temp_c:.0f}C"

        left = [f"{'>_' if i == self.nav_index else '  '} {name}" for i, (name, _) in enumerate(NAV_ITEMS)]
        right = [
            f"NODE     {readiness}",
            f"OP       {op[:18]}",
            f"PROFILE  {self.profiles.current.name}",
            f"LINK     {'ISOLATED' if a.active else 'LINKED'}",
            f"NET/GPS  {self._telemetry_flag(t.network)}/{self._telemetry_flag(t.gps)}",
            f"MESH     {self._telemetry_flag(t.mesh)}",
            f"CPU      {temp}",
            "",
            f"ASSETS   {assets:03d}",
            f"EVIDENCE {evidence:03d}",
            f"EVENTS   {events:03d}",
        ]
        lines = ["╔═ RAVEN // RVN-01 OPERATOR CONSOLE ═════════════════════════════╗"]
        for i in range(max(len(left), len(right))):
            l = left[i] if i < len(left) else ""
            r = right[i] if i < len(right) else ""
            lines.append(f"║ {l:<31}│ {r:<29}║")
        lines.append("╠════════════════════════════════╧══════════════════════════════╣")
        alert = " // ".join(warnings[:3]) if warnings else "ALL MONITORED SUBSYSTEMS NOMINAL"
        lines.append(f"║ READINESS::{readiness:<9} {alert[:45]:<45}║")
        lines.append("╚═══════════════════════════════════════════════════════════════╝")
        self.query_one("#body", OperatorPane).update("\n".join(lines))
        self.set_header(
            "ROOT@RVN-01:/FIELDOS# COMMAND",
            f"NODE::{readiness} // OPERATOR CONTROL",
            f"{self.operations.active.name} // {op}",
            "UP/DN NAV  ENTER OPEN  / QUERY  F2 SHELL  F8 CMD  F1 HELP  ^Q EXIT",
        )
        self.focus_body()

    def action_command_center(self) -> None:
        self.view = "command-center"
        self.hide_aux()
        t = self._telemetry_snapshot
        a = self._airgap_state()
        readiness, warnings = self._readiness(t)
        op = self.operations.active.id
        installed = sum(1 for tool in self.tools.all if tool.installed)
        total = len(self.tools.all)
        lines = [
            "╔═ COMMAND CENTER // MISSION SNAPSHOT ════════════════════════════╗",
            f"║ NODE      RVN-01                 STATE    {readiness:<18}║",
            f"║ OPERATION {op[:20]:<20} PROFILE  {self.profiles.current.name:<18}║",
            f"║ LINK      {'ISOLATED' if a.active else 'LINKED':<20} TOOLS    {installed:02d}/{total:02d} READY          ║",
            "╠═ SUBSYSTEMS ═══════════════════════════════════════════════════╣",
            f"║ NETWORK   {str(t.network)[:18]:<18} GPS      {str(t.gps)[:18]:<18}║",
            f"║ MESH      {str(t.mesh)[:18]:<18} CPU      {('--' if t.cpu_temp_c < 0 else f'{t.cpu_temp_c:.1f}C'):<18}║",
            "╠═ OPERATOR FLOW ════════════════════════════════════════════════╣",
            "║ 1 SELECT OPERATION   2 VERIFY NODE   3 OPEN TOOL/PLAYBOOK      ║",
            "║ 4 EXECUTE MANUALLY   5 CAPTURE EVIDENCE   6 REVIEW TIMELINE   ║",
            "╠═ ADVISORIES ═══════════════════════════════════════════════════╣",
        ]
        if warnings:
            lines.extend(f"║ ! {warning[:57]:<57}║" for warning in warnings[:3])
        else:
            lines.append("║ + NO ACTIVE READINESS WARNINGS                                 ║")
        lines.extend([
            "╠════════════════════════════════════════════════════════════════╣",
            "║ F3 OPERATIONS  F4 HARDWARE  F9 PLAYBOOKS  F12 INTEL  F2 SHELL ║",
            "╚════════════════════════════════════════════════════════════════╝",
        ])
        self.query_one("#body", OperatorPane).update("\n".join(lines))
        self.set_header(
            "ROOT@RVN-01:/FIELDOS# COMMAND-CENTER",
            "MISSION SNAPSHOT // READ-ONLY",
            "Operator remains in control of every execution step",
            "F3 OP  F4 HW  F9 PLAYBOOKS  F12 INTEL  F2 SHELL  ESC DASH",
        )
        self.focus_body()

    def action_help(self) -> None:
        if self.view != "help":
            self.return_view = self.view
        self.view = "help"
        self.hide_aux()
        self.query_one("#body", OperatorPane).update(
            ":: RVN-01 OPERATOR KEYMAP ::\n\n"
            "UP/DOWN    MOVE / SHELL HISTORY       ENTER      OPEN / RUN\n"
            "ESC        DASHBOARD                  /          GLOBAL QUERY\n"
            "F1         HELP                       F2         TERMINAL\n"
            "F3         OPERATIONS                 F4         HARDWARE\n"
            "F5         NOTES                      F8         COMMAND CENTER\n"
            "F9         PLAYBOOKS                  F10        THEME\n"
            "F11        PROFILE                    F12        INTELLIGENCE\n"
            "CTRL+Q     EXIT FIELD//OS\n\n"
            "OPERATOR RULE: inspect -> select -> stage -> review -> execute.\n"
            "FIELD//OS does not autonomously execute offensive actions."
        )
        self.set_header("ROOT@RVN-01:/FIELDOS# HELP", "OPERATOR KEYMAP", "800x480 keyboard-first controls", "ESC DASH")
        self.focus_body()

    def action_back(self) -> None:
        if self.view in {"command-center", "help"}:
            self.render_home()
            return
        super().action_back()
