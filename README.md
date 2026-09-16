# RAVEN // RVN-01

**Rugged Raspberry Pi 5 field computer running FIELD//OS.**

RAVEN is an offline-first field-computing platform for communications, navigation, receive-only RF, local networking, offline knowledge, operations and hardware awareness.

> Development hardware. Use radio, network and security capabilities only where lawful and authorised.

<!-- Concept render target: assets/rvn-01-concept.jpg -->

## Objective

Build a portable, self-contained field computer that remains useful without Internet access and behaves like a purpose-built appliance rather than a conventional Raspberry Pi desktop.

Core objectives:

- offline-first operation
- simple operator-focused interface
- modular hardware integration
- graceful degradation when peripherals are unavailable
- explicit operator control of radio, network and shell actions
- reliable recovery through Raspberry Pi OS, SSH and local tooling

## Project Scope

RAVEN combines a Raspberry Pi 5 hardware platform with **FIELD//OS**, a 7-inch graphical operator environment.

Current scope includes:

- offline maps and GNSS
- Meshtastic / LoRa communications
- receive-only SDR
- local network visibility and authorised diagnostics
- offline knowledge and reference material
- local files and field operations
- terminal access
- hardware, service and system health monitoring

AI/ASSIST is currently deferred. Development priority is the offline knowledge library, hardware commissioning and subsystem integration.

## FIELD//OS

The home screen is intentionally limited to **9 primary applications**.

| Application | Purpose |
| --- | --- |
| **RADIO** | Receive-only SDR and spectrum |
| **NAVIGATION** | Offline maps, GPS, waypoints and tracks |
| **MESH** | Meshtastic nodes and operator-controlled messaging |
| **NETWORK** | Local interfaces, devices and authorised diagnostics |
| **OPS** | Operations, evidence and timeline |
| **LIBRARY** | Categorised offline knowledge and references |
| **FILES** | Local storage and operation files |
| **TERMINAL** | Explicit operator-controlled shell |
| **RVN-01** | System, hardware, power and service health |

Optional hardware enhances its application only. Missing GPS, SDR or mesh hardware must never prevent FIELD//OS from starting.

## LIBRARY

LIBRARY provides structured offline knowledge inside FIELD//OS.

Current sections:

`RAVEN` · `RADIO` · `NAVIGATION` · `COMMS` · `CYBER` · `COMPUTING` · `EMERGENCY` · `MEDICAL` · `REPAIR` · `SURVIVAL` · `TRAVEL` · `GENERAL`

The library supports local articles, manuals, operator-selected documentation and companion Kiwix/ZIM collections.

Bootstrap supported open-source reference sources with:

```bash
bash scripts/bootstrap-knowledge.sh
```

See [Offline Knowledge Sources](docs/KNOWLEDGE-SOURCES.md).

## RVN-01

The **RVN-01** application is the system-health view for the cyberdeck.

It is responsible for presenting:

- CPU, temperature, memory and storage
- power and throttle state
- USB and attached hardware
- GPS, SDR, mesh and audio readiness
- Bluetooth and network state
- SSH / mDNS connectivity
- FIELD//OS and supporting service status

## Hardware

Current platform baseline:

- Raspberry Pi 5 — 8 GB
- Raspberry Pi Active Cooler
- 7-inch 800×480 touchscreen
- local storage
- powered USB expansion
- Bluetooth
- optional GNSS
- optional Meshtastic / LoRa
- optional RTL-SDR
- optional audio subsystem

See the [RVN-01 Hardware BOM](hardware/bom/RVN-01-BOM.md) for the current confirmed inventory and commissioning order.

## Current Focus

1. finish the FIELD//OS LIBRARY experience
2. commission arriving hardware modules
3. expand RVN-01 system-health telemetry
4. refine appliance boot and recovery behaviour
5. finalise the physical RVN-01 layout

## Repository

```text
fieldos/      FIELD//OS application and hardware adapters
config/       knowledge and configuration manifests
docs/         architecture, install and commissioning guides
deploy/       appliance and service configuration
scripts/      setup, diagnostics and knowledge tooling
hardware/     BOM and physical design material
tests/        automated tests
```

## Documentation

- [RVN-01 Hardware BOM](hardware/bom/RVN-01-BOM.md)
- [RVN-01 Commissioning](docs/RVN-01-COMMISSIONING.md)
- [Offline Knowledge Sources](docs/KNOWLEDGE-SOURCES.md)
- [Module Installation Guide](docs/MODULE-INSTALL-GUIDE.md)
- [FIELD//OS Architecture](docs/FIELD-OS-ARCHITECTURE.md)
- [Roadmap](docs/ROADMAP.md)

---

**RAVEN // RVN-01 // FIELD//OS // OFFLINE FIELD COMPUTER**
