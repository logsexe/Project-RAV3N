from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Input, Static

from fieldos.hardware.mock import MockTelemetryProvider


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
    """FIELD//OS V0.1 development dashboard."""

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

    #category-grid {
        grid-size: 3 3;
        grid-gutter: 1 1;
        height: 1fr;
    }

    .category {
        height: 100%;
        min-height: 4;
        background: #10161a;
        color: #d5dbd8;
        border: solid #343c41;
        text-style: bold;
    }

    .category:focus {
        background: #20292e;
        color: #ffffff;
        border: heavy #b7c2c7;
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
        Binding("left", "move_focus(-1)", "Left", show=False),
        Binding("right", "move_focus(1)", "Right", show=False),
        Binding("up", "move_focus(-3)", "Up", show=False),
        Binding("down", "move_focus(3)", "Down", show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.telemetry_provider = MockTelemetryProvider()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Vertical(id="shell"):
            with Vertical(id="identity"):
                yield Static("RAVEN // RVN-01", id="platform")
                yield Static(
                    "FIELD OPERATIONS TERMINAL // HW REV A // FIELD//OS V0.1",
                    id="designation",
                )

            yield Input(
                placeholder="SEARCH // tools, commands, sessions, knowledge",
                id="search",
            )

            with Grid(id="category-grid"):
                for name, description in CATEGORIES:
                    yield Button(
                        f"{name}\n{description}",
                        id=f"category-{name.lower()}",
                        classes="category",
                    )

            yield Static("SYSTEM TELEMETRY INITIALISING", id="telemetry")
            yield Static("RECON // ANALYSE // OPERATE", id="mission")

        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(1.5, self.refresh_telemetry)
        self.refresh_telemetry()
        buttons = list(self.query(".category"))
        if buttons:
            buttons[0].focus()

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
        buttons = list(self.query(".category"))
        if buttons:
            buttons[0].focus()

    def action_move_focus(self, delta: int) -> None:
        buttons = list(self.query(".category"))
        if not buttons:
            return

        focused = self.focused
        try:
            index = buttons.index(focused)
        except ValueError:
            buttons[0].focus()
            return

        target = max(0, min(len(buttons) - 1, index + delta))
        buttons[target].focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        category = event.button.id.removeprefix("category-").upper()
        self.notify(
            f"{category} MODULE // interface scaffold ready",
            title="RAVEN",
            timeout=2.0,
        )

    def on_input_submitted(self, event: Input.Submitted) -> None:
        query = event.value.strip()
        if not query:
            return
        self.notify(
            f'SEARCH // "{query}" // indexer coming next',
            title="FIELD//OS",
            timeout=3.0,
        )


if __name__ == "__main__":
    FieldOSApp().run()
