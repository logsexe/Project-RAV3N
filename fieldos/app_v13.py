from __future__ import annotations

from datetime import datetime

from textual.widgets import Static

from .app_v12 import FieldOSApp as V12FieldOSApp, NAV_ITEMS, OperatorPane


class FieldOSApp(V12FieldOSApp):
    """FIELD//OS V1.3 — compact 800x480-first RAVEN operator console."""

    TITLE = "RAVEN // FIELD//OS V1.3"
    CSS = """
    Screen { background: #000000; color: #79ff96; }
    #shell { height: 1fr; padding: 0 1; }
    #status { height: 1; color: #b8ffc5; background: #001407; text-style: bold; }
    #breadcrumb { height: 1; color: #38a951; }
    #title { height: 1; color: #d5ffdc; text-style: bold; }
    #description { height: 1; color: #57bb6d; }
    #body { height: 1fr; padding: 0 1; border: solid #16762f; background: #000301; }
    #body:focus { border: heavy #5cff7d; background: #001006; }
    #example { height: 1; color: #4da85f; padding: 0 1; }
    #search, #entry, #command { height: 3; border: tall #258c3e; background: #000502; color: #c5ffd1; }
    #search:focus, #entry:focus, #command:focus { border: tall #78ff94; }
    #terminal-tabs { height: 1; color: #78ff94; text-style: bold; }
    #terminal-output { height: 1fr; padding: 0 1; border: solid #16762f; background: #000000; color: #8aff9f; }
    #footer { height: 1; color: #64c878; background: #001407; text-align: center; }
    .hidden { display: none; }
    """

    def refresh_status(self) -> None:
        t = self.telemetry_provider.read()
        a = self._airgap_state()
        temp = "--" if t.cpu_temp_c < 0 else f"{t.cpu_temp_c:.0f}C"
        clock = datetime.now().strftime("%H:%M")
        self.query_one("#status", Static).update(
            f" RAVEN::RVN-01  |  FIELD//OS 1.3  |  {self.profiles.current.name:<8} | "
            f"{'ISOLATED' if a.active else 'LINKED':<8} | CPU {temp:<4} | {clock} "
        )

    def render_home(self) -> None:
        self.view = "home"
        self.hide_aux()
        t = self.telemetry_provider.read()
        a = self._airgap_state()
        op = self.operations.active.id
        assets = len(self.intelligence.list_assets(op))
        evidence = len(self.intelligence.list_evidence(op))
        events = len(self.intelligence.timeline(op, limit=999))
        temp = "--" if t.cpu_temp_c < 0 else f"{t.cpu_temp_c:.1f}C"

        left = [f"{'>_' if i == self.nav_index else '  '} {name}" for i, (name, _) in enumerate(NAV_ITEMS)]
        right = [
            "[ NODE::RVN-01 ]",
            f"OP      {op}",
            f"PROFILE {self.profiles.current.name}",
            f"LINK    {'AIRGAP' if a.active else 'ONLINE'}",
            "",
            f"ASSETS  {assets:03d}",
            f"EVID    {evidence:03d}",
            f"EVENTS  {events:03d}",
            "",
            f"NET     {self._telemetry_flag(t.network)}",
            f"GPS     {self._telemetry_flag(t.gps)}",
            f"MESH    {self._telemetry_flag(t.mesh)}",
            f"TEMP    {temp}",
        ]
        lines = ["╔═ RAVEN // FIELD OPERATIONS CONSOLE ═════════════════════════════╗"]
        for i in range(max(len(left), len(right))):
            l = left[i] if i < len(left) else ""
            r = right[i] if i < len(right) else ""
            lines.append(f"║ {l:<31}│ {r:<29}║")
        lines.append("╚════════════════════════════════╧══════════════════════════════╝")
        self.query_one("#body", OperatorPane).update("\n".join(lines))
        self.set_header(
            "ROOT@RVN-01:/FIELDOS# DASHBOARD",
            "ACCESS::OPERATOR // NODE ONLINE",
            f"{self.operations.active.name} // {self.operations.active.id}",
            "UP/DN NAV  ENTER OPEN  / SEARCH  F2 SHELL  ESC BACK  ^Q EXIT",
        )
        self.focus_body()

    def render_terminal(self) -> None:
        super().render_terminal()
        session = self.terminals.active
        self.set_header(
            f"ROOT@RVN-01:{session.cwd}$",
            f"TTY::{session.name} // {'EXEC' if session.running else 'IDLE'}",
            f"OP::{self.operations.active.id} // COMMAND CAPTURE ACTIVE",
            "ENTER EXEC  UP/DN HISTORY  TAB NEXT TTY  F6 NEW  F8 CLEAR  ESC DASH",
        )

    def render_tools_home(self) -> None:
        super().render_tools_home()
        self.set_header(
            "ROOT@RVN-01:/FIELDOS/ARSENAL#",
            "ARSENAL // MODULE INDEX",
            f"PROFILE::{self.profiles.current.name} // INSTALLED MODULES MARKED READY",
            "UP/DN CLASS  ENTER OPEN  / SEARCH  ESC DASH",
        )

    def render_assets(self) -> None:
        super().render_assets()
        self.set_header("ROOT@RVN-01:/FIELDOS/ASSETS#", "TARGET // ASSET REGISTRY", f"OP::{self.operations.active.id}", "/ SEARCH  ESC DASH")

    def render_evidence(self) -> None:
        super().render_evidence()
        self.set_header("ROOT@RVN-01:/FIELDOS/VAULT#", "EVIDENCE // HASH VAULT", f"OP::{self.operations.active.id} // SHA256", "ESC DASH")

    def action_back(self) -> None:
        # V1.3 contract: Esc from a primary module always returns to the dashboard.
        if self.view in {"terminal", "intelligence", "status", "sessions", "knowledge", "notes", "assets", "evidence", "settings", "playbooks", "tools-home"}:
            self.render_home()
            return
        super().action_back()
