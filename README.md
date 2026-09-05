# PROJECT RAV3N

> **RAVEN // RVN-01**  
> **FIELD OPERATIONS TERMINAL**  
> **HW REV A // FIELD//OS**

Project RAV3N is a rugged, modular Raspberry Pi 5 field-computing platform combining cyber-security, networking, DFIR, communications, navigation, RF and hardware-lab capabilities in a portable field terminal.

## Platform identity

| Field | Designation |
|---|---|
| Platform | RAVEN |
| Unit | RVN-01 |
| Role | Field Operations Terminal |
| Software | FIELD//OS |
| Hardware | REV A |
| Status | DEVELOPMENT |

## FIELD//OS V0.4

FIELD//OS is now designed around the physical 7-inch 800×480 RVN-01 display rather than a desktop-style dashboard. The interface uses progressive full-screen views so the current task gets the available display area.

Primary navigation:

`HOME -> MODULE -> TOOL -> RECIPE -> TERMINAL`

FIELD//OS V0.4 adds a persistent field-operations layer on top of the V0.3 appliance interface:

- Persistent operation/session records stored under `~/.fieldos/sessions/` by default
- Automatic `notes/`, `scans/`, `captures/`, `evidence/` and `exports/` directories per operation
- Timestamped operation notes
- Active operation identity in the compact top status bar
- Full-screen live local terminal with independent terminal sessions and command history
- Tool recipes staged into the terminal for review/editing before execution
- Guided operator playbooks for Network Triage, Windows IR, Evidence Intake, Wireless Survey and RF Observation
- Playbook steps can stage example commands directly into the terminal
- Global tool/recipe search, installed-tool detection and compact system status

Current primary libraries:

`BLUE // RED // NETWORK // FORENSICS // FIELD // COMMS // HARDWARE // RF // UTILITIES`

The tool manifest includes Nmap, Wireshark/tshark, tcpdump, Kismet, Zeek, mtr, iperf3, YARA, Sigma, Chainsaw, Hayabusa, osquery, Suricata, Nuclei, Amass, Volatility 3, Binwalk, ExifTool, hashdeep, Meshtastic, gpsd, qFlipper, sigrok, rtl_433, rtl_power, Gqrx, CyberChef, jq, yq, ripgrep, fzf, OpenSSL, curl, tmux, btop and more.

Curated repositories such as SquidSec CyberDeck, A-poc BlueTeam-Tools and A-poc RedTeam-Tools are treated as knowledge sources rather than instructions to install every referenced tool.

## Controls

- `Up / Down` — navigate current list
- `Right / Enter` — open/select/stage
- `Left / Esc` — back
- `/` — global search
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

Inside Operations, press `N` to create a new operation. Inside Notes, press `N` to add a timestamped note.

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
- `assets/` — branding, boot assets and renders

## Development status

**FIELD//OS V0.4 field-operations development + Hardware REV A prototyping**

The remaining major software milestones are offline knowledge indexing/SquidSec integration, favourites/recent tools, themes, exports, real hardware adapters and appliance-style startup. Hardware integration remains dependent on physical RVN-01 bring-up.

---

`RAVEN // RVN-01 // FIELD//OS // DEVELOPMENT UNIT`
