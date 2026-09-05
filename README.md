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

FIELD//OS is the operator environment for RAVEN. V0.1.3 is a keyboard-first Textual terminal dashboard with mock RVN-01 telemetry so development can continue before the Raspberry Pi arrives.

The dashboard uses a compact module list on the left and a module library pane on the right. Highlighting a module shows its indexed tools. The operator can now move into and out of each module library using the right and left arrow keys, then navigate the tools inside with up/down and select one with Enter.

Current primary sections:

`BLUE // RED // NETWORK // FORENSICS // FIELD // COMMS // HARDWARE // RF // UTILITIES`

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

- Up / Down — navigate the current list
- Right Arrow — enter the highlighted module library
- Left Arrow — return to the module list
- Enter — select the highlighted module or tool
- `/` — focus global search
- Esc — return focus to the module list / clear search
- Q — quit

Hardware status currently uses a mock provider. Real Pi, Meshtastic, GNSS, battery and network adapters will replace those mocks as hardware comes online.

### Current tool index

The initial manifest lives at `config/tools/core.yaml` and currently contains tools such as Nmap, Wireshark/tshark, tcpdump, Kismet, CyberChef, YARA, Chainsaw, Hayabusa, Volatility 3, Binwalk, Nuclei, osquery, Meshtastic, gpsd and rtl_433.

Curated repositories such as SquidSec CyberDeck, A-poc BlueTeam-Tools and A-poc RedTeam-Tools remain knowledge sources rather than instructions to install every tool they reference.

## Repository layout

- `docs/` — architecture, specifications, naming and roadmap
- `fieldos/` — FIELD//OS source
- `hardware/` — CAD, drawings, printable parts and BOM
- `config/` — themes and tool definitions
- `assets/` — branding, boot assets and renders

## Development status

**Phase 0 — Architecture & prototyping**

Current priorities are FIELD//OS V0.1.x, RVN-01 physical measurements, RVN-KB1 CAD, component layout and hardware BOM. Hardware-dependent integrations use mock adapters until the Raspberry Pi and peripherals are available.

---

`RAVEN // RVN-01 // FIELD//OS // DEVELOPMENT UNIT`
