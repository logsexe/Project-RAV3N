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

## RVN-01 capability groups

- **CYBER** — Blue Team, Red Team, network analysis and authorised security testing
- **DFIR** — event logs, memory, file and firmware analysis
- **COMMS** — Meshtastic / LoRa communications
- **NAV** — GNSS, maps, waypoints and tracks
- **RF** — receive-side SDR and spectrum tooling
- **LAB** — hardware interfaces, serial, USB and electronics diagnostics
- **FIELD** — sessions, notes, evidence and operational workflows

## Current hardware baseline

- Tactix Tough Case — Medium
- 65% wired mechanical keyboard — confirmed physical fit
- Raspberry Pi 5 8 GB — awaiting arrival
- Raspberry Pi Active Cooler
- Raspberry Pi M.2 HAT+
- Freenove 7-inch touchscreen
- Anker 4-port USB 3.0 hub
- Patriot 256 GB microSDXC
- Flipper Zero — removable field instrument

The keyboard is intended to sit flush in the lid using the RVN-KB1 removable retention system. Final printable CAD dimensions will be based on physical measurements and test fits rather than nominal product dimensions.

## FIELD//OS

FIELD//OS V0.2 is now a keyboard-first operator console rather than a static dashboard. It uses a persistent module rail on the left and a context-sensitive operator pane on the right.

Navigation is hierarchical:

`MODULE -> TOOL LIBRARY -> TOOL DETAIL -> COMMAND RECIPES`

The interface now includes breadcrumbs, active-pane highlighting, detected-tool status, manifest counts, local search across tools and recipe content, per-tool metadata, and curated operator command patterns. Recipe commands are displayed for review rather than auto-executed.

Current primary sections:

`BLUE // RED // NETWORK // FORENSICS // FIELD // COMMS // HARDWARE // RF // UTILITIES`

The core manifest now covers a much broader toolset including Nmap, Wireshark/tshark, tcpdump, Kismet, Zeek, mtr, iperf3, YARA, Sigma, Chainsaw, Hayabusa, osquery, Suricata, Nuclei, Amass, Volatility 3, Binwalk, ExifTool, hashdeep, Meshtastic, gpsd, qFlipper, sigrok, serial/I2C utilities, rtl_433, rtl_power, Gqrx, CyberChef, jq, yq, ripgrep, fzf, OpenSSL, curl, tmux and btop.

### Run the development build

Requires Python 3.11+.

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -e .
fieldos
```

Linux / macOS:

```bash
source .venv/bin/activate
pip install -e .
fieldos
```

You can also run it directly with:

```bash
python -m fieldos
```

### Current controls

- Up / Down — navigate the current module, tool or recipe list
- Right Arrow / Enter — move one level deeper
- Left Arrow — move one level back
- `/` — global search across tool metadata and recipe text
- Esc — return to dashboard/module rail
- Q — quit

Hardware status currently uses a mock provider. Real Pi, Meshtastic, GNSS, battery and network adapters will replace those mocks as hardware comes online.

### Tool manifest

The core manifest lives at `config/tools/core.yaml`. Manifest records can define category, subcategory, description, executable, offline capability, privilege requirements, authorised-use flags and operator recipes.

Curated repositories such as SquidSec CyberDeck, A-poc BlueTeam-Tools and A-poc RedTeam-Tools remain knowledge sources rather than instructions to install every tool they reference.

## Repository layout

- `docs/` — architecture, specifications, naming and roadmap
- `fieldos/` — FIELD//OS source
- `hardware/` — CAD, drawings, printable parts and BOM
- `config/` — themes and tool definitions
- `assets/` — branding, boot assets and renders

## Development status

**FIELD//OS V0.2 operator-console development + Hardware REV A prototyping**

Current priorities are deeper tool workflows, sessions, favourites/recent tools, offline knowledge indexing, real hardware adapters and RVN-01 physical integration.

---

`RAVEN // RVN-01 // FIELD//OS // DEVELOPMENT UNIT`
