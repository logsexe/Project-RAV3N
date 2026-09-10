from __future__ import annotations

import socket

from textual.widgets import Static

from .app_v14 import FieldOSApp as V14FieldOSApp
from .app_v12 import OperatorPane
from .plugins import PluginRegistry


V15_NAV_ITEMS = (
    ("DASHBOARD", "Operational overview"),
    ("TOOL CENTER", "Capability and command library"),
    ("PLUGINS", "FIELD//OS integration registry"),
    ("PLAYBOOKS", "Guided field workflows"),
    ("OPERATIONS", "Cases and field sessions"),
    ("ASSETS", "Tracked investigation entities"),
    ("EVIDENCE", "Collected and verified artefacts"),
    ("INTEL", "Timeline and intelligence state"),
    ("KNOWLEDGE", "Offline reference library"),
    ("TERMINAL", "Operator shell sessions"),
    ("HARDWARE", "RVN-01 system telemetry"),
    ("SETTINGS", "Profile and visual controls"),
)


class FieldOSApp(V14FieldOSApp):
    """FIELD//OS V1.5 — unified Tool Center and plugin capability registry."""

    TITLE = "RAVEN // FIELD//OS V1.5"

    def __init__(self) -> None:
        super().__init__()
        self.plugins = PluginRegistry.load_default()
        self.plugin_index = 0

    def refresh_status(self) -> None:
        t = self._telemetry_snapshot
        a = self._airgap_state()
        temp = "--" if t.cpu_temp_c < 0 else f"{t.cpu_temp_c:.0f}C"
        self.query_one("#status", Static).update(
            f" RVN-01 | OS 1.5 | OP {self.operations.active.id[:10]:<10} | "
            f"{self.profiles.current.name:<8} | {'ISOLATED' if a.active else 'LINKED':<8} | "
            f"NET {self._telemetry_flag(t.network):<2} GPS {self._telemetry_flag(t.gps):<2} "
            f"MESH {self._telemetry_flag(t.mesh):<2} | {temp:<4} | PLG {self.plugins.enabled_count():02d} "
        )

    def render_home(self) -> None:
        self.view = "home"
        self.hide_aux()
        t = self._telemetry_snapshot
        a = self._airgap_state()
        op = self.operations.active.id
        readiness, warnings = self._readiness(t)
        left = [f"{'>_' if i == self.nav_index else '  '} {name}" for i, (name, _) in enumerate(V15_NAV_ITEMS)]
        right = [
            f"NODE     {readiness}",
            f"OP       {op[:18]}",
            f"PROFILE  {self.profiles.current.name}",
            f"LINK     {'ISOLATED' if a.active else 'LINKED'}",
            f"NET/GPS  {self._telemetry_flag(t.network)}/{self._telemetry_flag(t.gps)}",
            f"MESH     {self._telemetry_flag(t.mesh)}",
            f"TOOLS    {self.tools.installed_count():02d}/{len(self.tools.all):02d}",
            f"PLUGINS  {self.plugins.enabled_count():02d}/{len(self.plugins.all):02d}",
        ]
        lines = ["╔═ RAVEN // FIELD//OS V1.5 ═══════════════════════════════════════╗"]
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
            "ROOT@RVN-01:/FIELDOS# DASHBOARD",
            "OPERATOR CONTROL // TOOL CENTER READY",
            "inspect -> select -> stage -> review -> execute",
            "UP/DN NAV  ENTER OPEN  / QUERY  F2 SHELL  F8 CMD  F1 HELP  ^Q EXIT",
        )
        self.focus_body()

    def render_tool_center(self) -> None:
        self.view = "tool-center"
        self.hide_aux()
        rows = []
        for i, (name, desc) in enumerate(self._tool_categories()):
            tools = self.tools.for_category(name.lower())
            ready = sum(1 for tool in tools if tool.installed)
            marker = ">_" if i == self.category_index else "  "
            rows.append(f"{marker} {name:<12} {ready:02d} READY / {len(tools):02d} INDEXED  // {desc}")
        rows.extend([
            "",
            f"   PLAYBOOKS    {len(self.playbooks.all):02d} AVAILABLE",
            f"   PLUGINS      {self.plugins.enabled_count():02d} ENABLED / {len(self.plugins.all):02d} INDEXED",
        ])
        self.query_one("#body", OperatorPane).update("\n".join(rows))
        self.set_header(
            "ROOT@RVN-01:/FIELDOS# TOOL-CENTER",
            "UNIFIED CAPABILITY INDEX",
            "Tool availability is inspected locally; execution remains operator-controlled",
            "ESC DASH  UP/DN CATEGORY  ENTER OPEN  / QUERY  F9 PLAYBOOKS",
        )
        self.focus_body()

    def _tool_categories(self):
        return (
            ("NETWORK", "Discovery / diagnostics"),
            ("OSINT", "Open-source intelligence / enrichment"),
            ("UTILITIES", "Operator utilities"),
            ("FIELD", "Field systems / sessions"),
            ("BLUE", "Defensive security / hunting"),
            ("FORENSICS", "DFIR / evidence analysis"),
            ("RF", "SDR / spectrum tools"),
            ("COMMS", "Meshtastic / messaging"),
            ("HARDWARE", "USB / serial / electronics"),
            ("RED", "Authorised testing / validation"),
        )

    def render_plugins(self) -> None:
        self.view = "plugins"
        self.hide_aux()
        items = self.plugins.all
        self.plugin_index = min(self.plugin_index, max(0, len(items) - 1))
        lines = [":: PLUGIN REGISTRY ::", ""]
        for i, plugin in enumerate(items):
            marker = ">_" if i == self.plugin_index else "  "
            state = "ENABLED" if plugin.enabled else "OFF"
            lines.append(f"{marker} {plugin.name[:22]:<22} [{state:<7}] {plugin.category.upper():<10} v{plugin.version}")
        if not items:
            lines.append("NO PLUGINS INDEXED")
        self.query_one("#body", OperatorPane).update("\n".join(lines))
        self.set_header(
            "ROOT@RVN-01:/FIELDOS# PLUGINS",
            "PLUGIN CAPABILITY REGISTRY",
            "Metadata-only V1.5 registry // no arbitrary plugin code auto-executes",
            "ESC DASH  UP/DN SELECT  ENTER INSPECT  SPACE ENABLE/DISABLE",
        )
        self.focus_body()

    def render_plugin_detail(self) -> None:
        items = self.plugins.all
        if not items:
            return
        plugin = items[self.plugin_index]
        self.view = "plugin-detail"
        self.hide_aux()
        requires = ", ".join(plugin.requires) if plugin.requires else "NONE"
        lines = [
            "┌─ PLUGIN DOSSIER ────────────────────────────────────────────────",
            f"│ ID         {plugin.id}",
            f"│ NAME       {plugin.name}",
            f"│ STATE      {'ENABLED' if plugin.enabled else 'DISABLED'}",
            f"│ CATEGORY   {plugin.category.upper()}",
            f"│ VERSION    {plugin.version}",
            f"│ PLATFORM   {plugin.platform}",
            f"│ REQUIRES   {requires}",
            f"│ PRIVILEGE  {plugin.privilege.upper()}",
            f"│ NETWORK    {plugin.network.upper()}",
            f"│ HARDWARE   {plugin.hardware.upper()}",
            f"│ EXECUTION  {plugin.execution.upper()}",
            "├─ PURPOSE",
            f"│ {plugin.description}",
            "├─ SAFETY",
            "│ V1.5 plugins declare capabilities only.",
            "│ No arbitrary plugin Python is imported or executed automatically.",
            "└─────────────────────────────────────────────────────────────────",
        ]
        self.query_one("#body", OperatorPane).update("\n".join(lines))
        self.set_header(
            f"ROOT@RVN-01:/FIELDOS# PLUGINS/{plugin.id}",
            plugin.name.upper(),
            "Capability manifest // operator-controlled integration",
            "ESC BACK  SPACE ENABLE/DISABLE",
        )
        self.focus_body()

    def action_status(self) -> None:
        """Hardware view using cached telemetry only; never blocks on gpspipe."""
        if self.view != "status":
            self.return_view = self.view
        self.view = "status"
        self.hide_aux()
        t = self._telemetry_snapshot
        a = self._airgap_state()
        try:
            interfaces = ", ".join(name for _, name in socket.if_nameindex()) or "NONE"
        except OSError:
            interfaces = "UNKNOWN"
        temp = "UNKNOWN" if t.cpu_temp_c < 0 else f"{t.cpu_temp_c:.1f} C"
        battery = "EXTERNAL / UNKNOWN" if t.battery_percent < 0 else f"{t.battery_percent}%"
        self.query_one("#body", OperatorPane).update(
            f"NODE        RVN-01\n"
            f"OPERATION   {self.operations.active.id}\n"
            f"PROFILE     {self.profiles.current.name}\n"
            f"AIRGAP      {'ACTIVE' if a.active else 'OFF'}\n"
            f"NETWORK     {t.network}\n"
            f"INTERFACES  {interfaces}\n"
            f"GPS         {t.gps}\n"
            f"MESH        {t.mesh}\n"
            f"CPU TEMP    {temp}\n"
            f"STORAGE     {t.storage_percent}%\n"
            f"BATTERY     {battery}\n\n"
            "TELEMETRY   BACKGROUND / NON-BLOCKING"
        )
        self.set_header(
            "ROOT@RVN-01:/FIELDOS# HARDWARE",
            "RVN-01 // HARDWARE STATUS",
            "Cached hardware state // background collector remains responsive",
            "ESC DASH  F8 COMMAND CENTER",
        )
        self.focus_body()

    def action_move_up(self) -> None:
        if self.view == "home":
            self.nav_index = max(0, self.nav_index - 1); self.render_home()
        elif self.view == "tool-center":
            self.category_index = max(0, self.category_index - 1); self.render_tool_center()
        elif self.view == "plugins":
            self.plugin_index = max(0, self.plugin_index - 1); self.render_plugins()
        else:
            super().action_move_up()

    def action_move_down(self) -> None:
        if self.view == "home":
            self.nav_index = min(len(V15_NAV_ITEMS) - 1, self.nav_index + 1); self.render_home()
        elif self.view == "tool-center":
            self.category_index = min(len(self._tool_categories()) - 1, self.category_index + 1); self.render_tool_center()
        elif self.view == "plugins":
            self.plugin_index = min(max(0, len(self.plugins.all) - 1), self.plugin_index + 1); self.render_plugins()
        else:
            super().action_move_down()

    def action_open(self) -> None:
        if self.view == "home":
            choice = V15_NAV_ITEMS[self.nav_index][0]
            if choice == "DASHBOARD": self.render_home()
            elif choice == "TOOL CENTER": self.render_tool_center()
            elif choice == "PLUGINS": self.render_plugins()
            elif choice == "PLAYBOOKS": self.action_playbooks()
            elif choice == "OPERATIONS": self.action_sessions()
            elif choice == "ASSETS": self.render_assets()
            elif choice == "EVIDENCE": self.render_evidence()
            elif choice == "INTEL": self.action_intelligence()
            elif choice == "KNOWLEDGE": self.render_knowledge()
            elif choice == "TERMINAL": self.action_terminal()
            elif choice == "HARDWARE": self.action_status()
            elif choice == "SETTINGS": self.render_settings()
            return
        if self.view == "tool-center":
            name, _ = self._tool_categories()[self.category_index]
            from fieldos import app_v05
            for i, (category, _) in enumerate(app_v05.CATEGORIES):
                if category == name:
                    self.category_index = i
                    break
            self.render_library()
            return
        if self.view == "plugins":
            self.render_plugin_detail()
            return
        super().action_open()

    def action_toggle_plugin(self) -> None:
        if self.view not in {"plugins", "plugin-detail"} or not self.plugins.all:
            return
        self.plugins.toggle(self.plugin_index)
        if self.view == "plugin-detail":
            self.render_plugin_detail()
        else:
            self.render_plugins()
        self.refresh_status()

    def on_key(self, event) -> None:
        if event.key == "space" and self.view in {"plugins", "plugin-detail"}:
            self.action_toggle_plugin()
            event.stop()

    def action_back(self) -> None:
        if self.view == "plugin-detail":
            self.render_plugins(); return
        if self.view in {"plugins", "tool-center", "status"}:
            self.render_home(); return
        super().action_back()
