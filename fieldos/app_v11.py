from __future__ import annotations

from textual.binding import Binding
from textual.widgets import Static

from fieldos.airgap import AirgapController
from fieldos.app_v1 import FieldOSApp as BaseFieldOSApp
from fieldos.app_v05 import OperatorPane
from fieldos.engine import OperationsEngine
from fieldos.profiles import ProfileManager


class FieldOSApp(BaseFieldOSApp):
    """FIELD//OS V1.1 adds structured operations, profiles and isolation state."""

    BINDINGS = BaseFieldOSApp.BINDINGS + [
        Binding("f11", "profile", "Profile"),
        Binding("f12", "intelligence", "Intel"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.profiles = ProfileManager()
        self.intelligence = OperationsEngine()
        self.airgap = AirgapController()

    def refresh_status(self) -> None:
        t = self.telemetry_provider.read()
        profile = self.profiles.current.name
        airgap = self.airgap.status()
        isolation = " AIRGAP" if airgap.active else ""
        battery = "EXT" if t.battery_percent < 0 else f"{t.battery_percent}%"
        self.query_one("#status", Static).update(
            f"RAVEN // {self.operations.active.id:<12} {profile:<9}{isolation:<8} BAT {battery}"
        )

    def action_profile(self) -> None:
        profile = self.profiles.next()
        self.refresh_status()
        message = f"PROFILE // {profile.name} // NET {profile.network_policy} // HW {profile.hardware_policy}"
        if profile.name == "AIRGAP":
            message += " // use fieldos-control airgap on --confirm to isolate"
        self.notify(message, title="FIELD//OS", timeout=3.0)
        if self.view == "status":
            self.action_status()

    def action_intelligence(self) -> None:
        if self.view != "intelligence":
            self.return_view = self.view
        self.view = "intelligence"
        self.hide_aux()
        operation_id = self.operations.active.id
        assets = self.intelligence.list_assets(operation_id)
        evidence = self.intelligence.list_evidence(operation_id)
        events = self.intelligence.timeline(operation_id, limit=8)

        lines = [
            f"OPERATION   {operation_id}",
            f"PROFILE     {self.profiles.current.name}",
            f"ASSETS      {len(assets)}",
            f"EVIDENCE    {len(evidence)}",
            "",
            "ASSETS",
        ]
        lines.extend(f"{item.id:<12} {item.kind:<10} {item.value}" for item in assets[:8])
        if not assets:
            lines.append("NONE")
        lines.extend(["", "EVIDENCE"])
        lines.extend(f"{item.id:<12} {item.sha256[:10]} {'ENC' if item.encrypted else 'RAW'} {item.source_name}" for item in evidence[:8])
        if not evidence:
            lines.append("NONE")
        lines.extend(["", "TIMELINE"])
        lines.extend(f"{item.timestamp[11:19]} {item.event_type:<9} {item.summary}" for item in reversed(events))
        if not events:
            lines.append("NONE")

        self.query_one("#body", OperatorPane).update("\n".join(lines))
        self.set_header("FIELD//OS > INTELLIGENCE", "ASSET / EVIDENCE ENGINE", "Structured operational state", "ESC BACK  F11 PROFILE")
        self.focus_body()

    def action_status(self) -> None:
        if self.view != "status":
            self.return_view = self.view
        self.view = "status"
        self.hide_aux()
        t = self.telemetry_provider.read()
        d = self.telemetry_provider.details()
        airgap = self.airgap.status()
        assets = len(self.intelligence.list_assets(self.operations.active.id))
        evidence = len(self.intelligence.list_evidence(self.operations.active.id))
        battery = "EXTERNAL / UNKNOWN" if t.battery_percent < 0 else f"{t.battery_percent}%"
        temp = "UNKNOWN" if t.cpu_temp_c < 0 else f"{t.cpu_temp_c:.1f} C"
        interfaces = ", ".join(d.interfaces) if d.interfaces else "NONE"
        self.query_one("#body", OperatorPane).update(
            f"OPERATION   {self.operations.active.id}\n"
            f"PROFILE     {self.profiles.current.name}\n"
            f"AIRGAP      {'ACTIVE' if airgap.active else 'OFF'}\n"
            f"HOSTNAME    {d.hostname}\n"
            f"PLATFORM    {d.platform}\n"
            f"NETWORK     {t.network}\n"
            f"INTERFACES  {interfaces}\n"
            f"GPS         {t.gps}\n"
            f"MESH        {t.mesh}\n"
            f"CPU TEMP    {temp}\n"
            f"STORAGE     {t.storage_percent}%\n"
            f"BATTERY     {battery}\n"
            f"ASSETS      {assets}\n"
            f"EVIDENCE    {evidence}\n"
            f"THEME       {self.themes.current.name}"
        )
        self.set_header("FIELD//OS > STATUS", "RVN-01 // SYSTEM STATUS", "Platform, profile and operational readiness", "ESC BACK  F11 PROFILE  F12 INTEL")
        self.focus_body()
