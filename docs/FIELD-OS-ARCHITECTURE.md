# FIELD//OS Architecture

## Purpose

FIELD//OS is the operator environment for RAVEN. It is not intended to replace Linux at the kernel/driver layer. A reliable ARM64 Linux base provides hardware support while FIELD//OS provides the appliance-like RAVEN experience.

```text
RAVEN // RVN-01
        |
        v
FIELD//OS SHELL
        |
+-------+-------+-------+
|       |       |       |
CYBER  FIELD   COMMS   HARDWARE
        |
        v
ARM64 LINUX BASE
```

## V0.1 goals

1. Keyboard-first dashboard
2. Category navigation
3. Global search
4. Tool manifests
5. SquidSec knowledge integration
6. Session storage
7. Mock hardware telemetry

The application must remain usable on a development PC before RVN-01 hardware is complete.

## Primary navigation

```text
BLUE
RED
NETWORK
FORENSICS
FIELD
COMMS
HARDWARE
RF
UTILITIES
```

Suggested controls:

```text
UP/DOWN       Navigate
LEFT/RIGHT    Change section
ENTER         Select / launch
ESC           Back
/             Global search
?             Context help
Q             Quit
```

## Core subsystems

```text
fieldos/
  core/       application state and event bus
  ui/         dashboard and navigation
  search/     unified local search
  sessions/   operational session management
  hardware/   hardware detection and telemetry
  knowledge/  offline reference indexing
  adapters/   integrations with external tools
  manifests/  tool metadata
```

## Tool model

FIELD//OS should understand tools rather than only launch binaries. A manifest may define:

```yaml
name: Hayabusa
category: blue
subcategory: dfir
command: hayabusa
platforms:
  - linux-arm64
installed: false
offline: true
requires_root: false
accepts:
  - evtx
outputs:
  - csv
  - json
```

This metadata enables filtering, search, context help and purpose-built launch screens.

## Knowledge sources

Initial indexed sources are planned to include:

- SquidSec CyberDeck command library
- A-poc/BlueTeam-Tools
- A-poc/RedTeam-Tools
- local tool documentation
- selected Sigma/YARA material
- operator notes

Curated repositories are treated as knowledge sources. Their existence does not imply installing every referenced security tool.

## Sessions

A session groups activity for a specific task or field operation:

```text
sessions/<session-id>/
  metadata.json
  notes/
  scans/
  captures/
  evidence/
  exports/
```

Longer term, normalised session metadata will live in SQLite so FIELD//OS can build timelines and cross-tool views.

## Hardware abstraction

Hardware-dependent UI must communicate through adapters. Missing hardware returns `NOT PRESENT`; development builds may provide mock telemetry. This prevents FIELD//OS from becoming tightly coupled to Raspberry Pi GPIO or one exact peripheral revision.

Planned adapters include:

- system telemetry
- Meshtastic
- GNSS/gpsd
- Flipper Zero
- SDR
- Wi-Fi interfaces
- future RVN system controller

## Future shell direction

The final appliance experience may use a lightweight Wayland environment inspired by keyboard-first systems such as Omarchy, but FIELD//OS must not depend on stock Omarchy or x86-only components. The Pi 5 target remains ARM64.
