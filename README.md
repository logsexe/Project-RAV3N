# PROJECT RAV3N

> **RAVEN // RVN-01**  
> **FIELD OPERATIONS TERMINAL**  
> **HW REV A // FIELD//OS V1.0**

Project RAV3N is a rugged, modular Raspberry Pi 5 field-computing platform combining cyber-security, networking, DFIR, communications, navigation, RF and hardware-lab capabilities in a portable field terminal.

## FIELD//OS V1.0

FIELD//OS is the keyboard-first operator environment for RVN-01. It is designed around the physical 7-inch 800×480 display and uses progressive full-screen views rather than a desktop dashboard.

Primary workflow:

`HOME -> MODULE -> TOOL -> RECIPE -> TERMINAL`

V1 software includes:

- BLUE / RED / NETWORK / FORENSICS / FIELD / COMMS / HARDWARE / RF / UTILITIES libraries
- Curated tool manifests with installed-state detection and operator command recipes
- Full-screen local terminal with multiple sessions, history and staged recipe commands
- Persistent terminal working-directory changes with `cd`
- `Ctrl+C` interruption for a running FIELD//OS command process
- Automatic command transcript capture into the active operation
- Persistent operations/cases with notes, commands, scans, captures, evidence and exports folders
- ZIP export snapshots for the active operation
- Network Triage, Windows IR, Evidence Intake, Wireless Survey and RF Observation playbooks
- Persistent favourites and recent tools
- Bundled offline knowledge and combined global search
- Optional indexing of local SquidSec CyberDeck, BlueTeam-Tools and RedTeam-Tools checkouts
- Real best-effort system telemetry with safe fallbacks when hardware is absent
- Network-interface discovery
- gpsd/gpspipe readiness detection
- Meshtastic CLI / serial readiness detection
- Battery/sysfs, storage and CPU-temperature telemetry where exposed by the host
- Five low-light themes: Phosphor, Amber CRT, Ice Blue, Red Alert and Monochrome
- `fieldos-check` host/hardware compatibility report
- Raspberry Pi / Debian bootstrap script and tty1 appliance-style systemd service
- Cross-platform CI for Python 3.11 and 3.12 on Linux and Windows

Hardware-dependent capabilities report `NOT PRESENT`, `NO FIX`, `SERIAL`, or similar status rather than preventing FIELD//OS from starting.

## Controls

- `Up / Down` — navigate
- `Right / Enter` — open/select/stage
- `Left / Esc` — back
- `/` — global search
- `K` — offline knowledge
- `F` — favourites; on a tool page, toggle favourite
- `R` — recent tools
- `F1` — help
- `F2` — terminal
- `F3` — operations/sessions
- `F4` — system status
- `F5` — operation notes
- `F9` — playbooks
- `F10` — cycle theme
- `Ctrl+Q` — quit

Inside the terminal:

- `Tab` / `Shift+Tab` — next / previous terminal
- `F6` — new terminal
- `F7` — close terminal
- `F8` — clear terminal
- `Ctrl+C` — request termination of the running command

Inside Operations, `N` creates a new operation and `E` exports the active operation. Inside Notes, `N` adds a timestamped note.

## Runtime data

Default runtime root:

```text
~/.fieldos/
├─ state.json
├─ exports/
└─ sessions/
   └─ FIELD-001/
      ├─ metadata.json
      ├─ notes/
      ├─ commands/
      ├─ scans/
      ├─ captures/
      ├─ evidence/
      └─ exports/
```

Set `FIELDOS_DATA_DIR` to override the runtime root.

## Offline knowledge

Bundled reference content lives in `config/knowledge/core.yaml`.

To index local documentation/repository checkouts:

Windows PowerShell:

```powershell
$env:FIELDOS_KNOWLEDGE_PATHS="C:\Tools\CyberDeck;C:\Tools\BlueTeam-Tools;C:\Tools\RedTeam-Tools"
fieldos
```

Linux:

```bash
export FIELDOS_KNOWLEDGE_PATHS="$HOME/tools/CyberDeck:$HOME/tools/BlueTeam-Tools:$HOME/tools/RedTeam-Tools"
fieldos
```

FIELD//OS indexes local reference content only; it does not automatically install every tool referenced by those repositories.

## Development / Windows run

Requires Python 3.11+.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
fieldos-check
fieldos
```

## RVN-01 / Raspberry Pi install

On Raspberry Pi OS / Debian ARM64:

```bash
git clone https://github.com/logsexe/Project-RAV3N.git
cd Project-RAV3N
sudo bash scripts/install-rvn01.sh "$USER"
/opt/fieldos/.venv/bin/fieldos-check
```

When the display, keyboard and tty1 behaviour have been physically validated, enable appliance boot:

```bash
sudo systemctl disable getty@tty1.service
sudo systemctl enable fieldos@$USER.service
sudo systemctl start fieldos@$USER.service
```

The installer intentionally does not bulk-install security, SDR, GNSS or Meshtastic tooling. Commission each hardware/software module deliberately.

## Current hardware baseline

- Tactix Tough Case — Medium
- 65% wired mechanical keyboard
- Raspberry Pi 5 8 GB
- Raspberry Pi Active Cooler
- Raspberry Pi M.2 HAT+
- Freenove 7-inch touchscreen
- Anker 4-port USB 3.0 hub
- Patriot 256 GB microSDXC
- Flipper Zero — removable field instrument

## Repository layout

- `fieldos/` — FIELD//OS source
- `config/tools/` — tool definitions and command recipes
- `config/playbooks/` — guided operator workflows
- `config/knowledge/` — bundled offline knowledge
- `deploy/` — appliance/service configuration
- `scripts/` — RVN-01 bootstrap tooling
- `docs/` — architecture, specifications and commissioning documentation
- `hardware/` — CAD, drawings, printable parts and BOM
- `assets/` — branding, boot assets and renders

## Release state

**FIELD//OS software baseline: V1.0.0**

The software architecture is now considered feature-complete for RVN-01 V1. Remaining work is physical commissioning: validating the Pi, touchscreen, keyboard, power system, cooling, GNSS, Meshtastic, dedicated Wi-Fi and SDR hardware on the actual unit.

---

`RAVEN // RVN-01 // FIELD//OS V1.0 // DEVELOPMENT UNIT`
