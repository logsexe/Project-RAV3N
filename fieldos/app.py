from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, Label, ListItem, ListView, Static

from fieldos.hardware.mock import MockTelemetryProvider
from fieldos.tools import ToolIndex


CATEGORIES = [
    ("BLUE", "Defensive security / hunting"),
    ("RED", "Authorised testing / validation"),
    ("NETWORK", "Discovery / packet analysis"),
    ("FORENSICS", "DFIR / evidence analysis"),
    ("FIELD", "Sessions / notes / navigation"),
    ("COMMS", "Meshtastic / messaging"),
    ("HARDWARE", "USB / serial / electronics"),
    ("RF", "SDR / spectrum tools"),
    ("UTILITIES", "Operator utilities"),
]


class FieldOSApp(App[None]):
    """FIELD//OS V0.1.2 development dashboard."""

    TITLE = "RAVEN // RVN-01 // FIELD//OS"
    SUB_TITLE = "FIELD OPERATIONS TERMINAL // DEVELOPMENT UNIT"

    CSS = """
    Screen {
        background: #070a0c;
        color: #d7ddd9;
    }

    Header {
        background: #0c1114;
        color: #d7ddd9;
        border-bottom: solid #586067;
    }

    #shell {
        height: 1fr;
        padding: 1 2;
    }

    #identity {
        height: auto;
        margin-bottom: 1;
    }

    #platform {
        text-style: bold;
        color: #f0f2ef;
    }

    #designation {
        color: #7f8b91;
    }

    #search {
        margin: 0 0 1 0;
        border: tall #40484d;
        background: #0b1013;
    }

    #search:focus {
        border: tall #b5c0c5;
    }

    #workspace {
        height: 1fr;
    }

    #category-list {
        width: 30;
        min-width: 24;
        height: 1fr;
        background: #0a0f12;
        border-right: solid #343c41;
        padding-right: 1;
    }

    #category-list > ListItem {
        height: 3;
        padding: 0 1;
        color: #879198;
        background: #0a0f12;
        border-left: solid #151c20;
    }

    #category-list > ListItem.active {
        color: #ffffff;
        background: #283238;
        text-style: bold;
        border-left: heavy #d7ddd9;
    }

    #category-list:focus > ListItem.active {
        color: #ffffff;
        background: #344149;
        border-left: heavy #ffffff;
    }

    .category-title {
        width: 1fr;
    }

    #content {
        width: 1fr;
        height: 1fr;
        padding: 0 2;
    }

    #content-title {
        height: 2;
        color: #f0f2ef;
        text-style: bold;
    }

    #content-description {
        height: 2;
        color: #7f8b91;
    }

    #content-body {
        height: 1fr;
        padding-top: 1;
        color: #c3cbce;
    }

    #telemetry {
        height: 3;
        margin-top: 1;
        padding: 0 1;
        background: #0c1114;
        border-top: solid #394146;
        border-bottom: solid #394146;
        content-align: center middle;
        color: #aeb8bc;
    }

    #mission {
        height: 1;
        margin-top: 1;
        color: #5f6a70;
        text-align: center;
    }

    Footer {
        background: #0c1114;
        color: #7f8b91;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("/", "search", "Search"),
        Binding("escape", "dashboard", "Dashboard"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.telemetry_provider = MockTelemetryProvider()
        self.tools = ToolIndex.load_default()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Vertical(id="shell"):
            with Vertical(id="identity"):
                yield Static("RAVEN // RVN-01", id="platform")
                yield Static(
                    "FIELD OPERATIONS TERMINAL // HW REV A // FIELD//OS V0.1.2",
                    id="designation",
                )

            yield Input(
                placeholder="SEARCH // tools, categories, commands, knowledge",
                id="search",
            )

            with Horizontal(id="workspace"):
                yield ListView(
                    *[
                        ListItem(
                            Label(f"{name}\n{description}", classes="category-title"),
                            id=f"category-{name.lower()}",
                        )
                        for name, description in CATEGORIES
                    ],
                    id="category-list",
                )

                with Vertical(id="content"):
                    yield Static("BLUE // MODULE", id="content-title")
                    yield Static("Defensive security / hunting", id="content-description")
                    yield Static("", id="content-body")

            yield Static("SYSTEM TELEMETRY INITIALISING", id="telemetry")
            yield Static("RECON // ANALYSE // OPERATE", id="mission")

        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(1.5, self.refresh_telemetry)
        self.refresh_telemetry()
        category_list = self.query_one("#category-list", ListView)
        category_list.index = 0
        category_list.focus()
        self.set_active_category(0)
        self.render_category("BLUE")

    def refresh_telemetry(self) -> None:
        telemetry = self.telemetry_provider.read()
        line = (
            f"MESH {telemetry.mesh}   //   "
            f"GPS {telemetry.gps}   //   "
            f"NET {telemetry.network}   //   "
            f"CPU {telemetry.cpu_temp_c:.1f}C   //   "
            f"STG {telemetry.storage_percent}%   //   "
            f"BAT {telemetry.battery_percent}%"
        )
        self.query_one("#telemetry", Static).update(line)

    def action_search(self) -> None:
        self.query_one("#search", Input).focus()

    def action_dashboard(self) -> None:
        search = self.query_one("#search", Input)
        search.value = ""
        category_list = self.query_one("#category-list", ListView)
        category_list.focus()
        index = category_list.index or 0
        self.set_active_category(index)
        self.render_category(CATEGORIES[index][0])

    def set_active_category(self, index: int) -> None:
        items = list(self.query("#category-list > ListItem"))
        for item_index, item in enumerate(items):
            item.set_class(item_index == index, "active")

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.item is None or not event.item.id:
            return
        category_list = self.query_one("#category-list", ListView)
        index = category_list.index or 0
        self.set_active_category(index)
        category = event.item.id.removeprefix("category-").upper()
        self.render_category(category)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.item is None or not event.item.id:
            return
        category_list = self.query_one("#category-list", ListView)
        index = category_list.index or 0
        self.set_active_category(index)
        category = event.item.id.removeprefix("category-").upper()
        self.render_category(category)
        self.notify(f"{category} MODULE // READY", title="RAVEN", timeout=1.5)

    def render_category(self, category: str) -> None:
        description = next(
            (desc for name, desc in CATEGORIES if name == category),
            "FIELD//OS module",
        )
        tools = self.tools.for_category(category.lower())

        self.query_one("#content-title", Static).update(f"{category} // MODULE")
        self.query_one("#content-description", Static).update(description)

        if not tools:
            body = (
                "STATUS      READY\n"
                "TOOLS       NONE INDEXED YET\n\n"
                "This module is online, but no tool manifests currently map to it."
            )
        else:
            lines = [
                "STATUS      READY",
                f"TOOLS       {len(tools)} INDEXED",
                "",
            ]
            for tool in tools:
                subcategory = f" // {tool.subcategory}" if tool.subcategory else ""
                lines.append(
                    f"> {tool.name:<24} [{tool.priority.upper()}]{subcategory}"
                )
            body = "\n".join(lines)

        self.query_one("#content-body", Static).update(body)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        query = event.value.strip()
        if not query:
            self.action_dashboard()
            return

        matches = self.tools.search(query)
        self.query_one("#content-title", Static).update(f'SEARCH // "{query.upper()}"')
        self.query_one("#content-description", Static).update(
            f"{len(matches)} result(s) in local FIELD//OS manifest index"
        )

        if not matches:
            body = "NO MATCHES\n\nTry a tool name, category, subcategory or priority."
        else:
            lines = []
            for tool in matches[:20]:
                subcategory = f" // {tool.subcategory}" if tool.subcategory else ""
                lines.append(
                    f"> {tool.name:<24} {tool.category.upper()}{subcategory} "
                    f"[{tool.priority.upper()}]"
                )
            body = "\n".join(lines)

        self.query_one("#content-body", Static).update(body)


if __name__ == "__main__":
    FieldOSApp().run()
