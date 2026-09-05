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

The keyboard is intended to sit flush in a custom 3D-printed lid cradle/bezel. Final CAD dimensions will be based on physical measurements rather than nominal product dimensions.

## FIELD//OS

FIELD//OS is the operator environment for RAVEN. V0.1 is being designed as a keyboard-first terminal dashboard inspired by the fast navigation and searchable command-library experience of SquidSec, while expanding into sessions, tool adapters, hardware telemetry and offline knowledge.

Planned primary sections:

`BLUE // RED // NETWORK // FORENSICS // FIELD // COMMS // HARDWARE // RF // UTILITIES`

## Repository layout

- `docs/` — architecture, specifications, naming and roadmap
- `fieldos/` — FIELD//OS source
- `hardware/` — CAD, drawings, printable parts and BOM
- `config/` — themes and tool definitions
- `assets/` — branding, boot assets and renders

## Development status

**Phase 0 — Architecture & prototyping**

Current priorities are FIELD//OS V0.1, RVN-01 physical measurements, keyboard cradle CAD, component layout and hardware BOM. Hardware-dependent integrations will use mock adapters until the Raspberry Pi and peripherals are available.

---

`RAVEN // RVN-01 // FIELD//OS // DEVELOPMENT UNIT`
