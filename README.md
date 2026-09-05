# PROJECT RAV3N

> **RAVEN // RVN-01**  
> **FIELD OPERATIONS TERMINAL**  
> **HW REV A // FIELD//OS**

Project RAV3N is a rugged, modular Raspberry Pi 5 field-computing platform combining cyber-security, networking, DFIR, communications, navigation, RF and hardware-lab capabilities in a portable field terminal.

## FIELD//OS V0.5

FIELD//OS is built around the physical 7-inch 800×480 RVN-01 display. The interface uses progressive full-screen views so the current task receives the usable display area.

Primary workflow:

`HOME -> MODULE -> TOOL -> RECIPE -> TERMINAL`

FIELD//OS V0.5 now includes:

- Persistent operations/sessions under `~/.fieldos/sessions/`
- Per-operation `notes/`, `scans/`, `captures/`, `evidence/` and `exports/` directories
- Timestamped operation notes
- ZIP export snapshots for the active operation
- Full-screen live local terminal with independent terminal sessions and command history
- Curated tool recipes staged for review/editing before execution
- Guided Network Triage, Windows IR, Evidence Intake, Wireless Survey and RF Observation playbooks
- Persistent favourite tools and recent-tool history
- Bundled offline knowledge reference entries
- Combined global search across tools, recipes, commands and offline knowledge
- Optional local documentation/repository indexing via `FIELDOS_KNOWLEDGE_PATHS`
- Local SquidSec CyberDeck, A-poc BlueTeam-Tools and A-poc RedTeam-Tools checkouts can be indexed without automatically installing their referenced tools

Current primary libraries:

`BLUE // RED // NETWORK // FORENSICS // FIELD // COMMS // HARDWARE // RF // UTILITIES`

## Controls

- `Up / Down` — navigate current list
- `Right / Enter` — open/select/stage
- `Left / Esc` — back
- `/` — global search
- `K` — offline knowledge
- `F` — favourites; from a tool page, toggle that tool as favourite
- `R` — recent tools
- `F1` — help
- `F2` — terminal
- `F3` — operations/sessions
- `F4` — system status
- `F5` — operation notes
- `F9` — playbooks

Inside the terminal:

- `Tab` — next terminal
- `Shift+Tab` — previous terminal
- `F6` — new terminal
- `F7` — close terminal
- `F8` — clear terminal

Inside Operations, press `N` to create a new operation and `E` to export the active operation as a ZIP snapshot. Inside Notes, press `N` to add a timestamped note.

## Offline knowledge

Bundled FIELD//OS reference content lives in `config/knowledge/core.yaml`.

To index local documentation or repository checkouts, set `FIELDOS_KNOWLEDGE_PATHS` before launching FIELD//OS. Multiple locations can be supplied using the host operating system path separator.

Windows PowerShell example:

```powershell
$env:FIELDOS_KNOWLEDGE_PATHS="C:\Tools\CyberDeck;C:\Tools\BlueTeam-Tools;C:\Tools\RedTeam-Tools"
fieldos
```

Linux example:

```bash
export FIELDOS_KNOWLEDGE_PATHS="$HOME/tools/CyberDeck:$HOME/tools/BlueTeam-Tools:$HOME/tools/RedTeam-Tools"
fieldos
```

FIELD//OS indexes Markdown, text, RST, YAML and JSON locally. The adapter is an offline search layer; it does not automatically install tools.

## Run the development build

Requires Python 3.11+.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
fieldos
```

Linux / macOS:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
fieldos
```

You can also run it with:

```bash
python -m fieldos
```

Set `FIELDOS_DATA_DIR` to override the default `~/.fieldos` runtime-data directory.

## Current hardware baseline

- Tactix Tough Case — Medium
- 65% wired mechanical keyboard — confirmed physical fit
- Raspberry Pi 5 8 GB
- Raspberry Pi Active Cooler
- Raspberry Pi M.2 HAT+
- Freenove 7-inch touchscreen
- Anker 4-port USB 3.0 hub
- Patriot 256 GB microSDXC
- Flipper Zero — removable field instrument

## Repository layout

- `docs/` — architecture, specifications, naming and roadmap
- `fieldos/` — FIELD//OS source
- `hardware/` — CAD, drawings, printable parts and BOM
- `config/tools/` — tool definitions and command recipes
- `config/playbooks/` — guided operator workflows
- `config/knowledge/` — bundled offline knowledge records
- `assets/` — branding, boot assets and renders

## Development status

**FIELD//OS V0.5 offline-knowledge/operator-state development + Hardware REV A prototyping**

The next major software block is V0.6: theme/low-light profiles, real Pi telemetry, GNSS and Meshtastic adapters, result capture into operation folders, ARM64 bootstrap/installation tooling and appliance-style startup.

---

`RAVEN // RVN-01 // FIELD//OS // DEVELOPMENT UNIT`
