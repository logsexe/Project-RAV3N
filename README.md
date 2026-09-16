# RAVEN // RVN-01

**Rugged Raspberry Pi 5 field computer running FIELD//OS.**

RAVEN is an offline-first field-computing platform combining a Pi 5 hardware build with **FIELD//OS**, a 7-inch graphical operator environment, for communications, navigation, receive-only RF, local networking, offline knowledge, operations and hardware awareness.

> Development hardware. Use radio, network and security capabilities only where lawful and authorised.

## Scope

- **Offline-first**: every feature works without Internet access; optional hardware (GPS, SDR, mesh) enhances FIELD//OS but its absence must never prevent it from starting — missing modules report `NOT PRESENT` rather than failing.
- **Operator-focused appliance**: a single full-screen application with a fixed 9-tile home screen, not a conventional desktop.
- **Explicit control**: radio, network and shell actions are operator-initiated, never automatic.

AI/ASSIST (local LLM integration) is implemented at the adapter level (`fieldos/offline_ai.py`) but not yet wired into the UI — deferred behind the offline knowledge library and hardware commissioning.

## FIELD//OS

The home screen is intentionally limited to **9 primary applications**:

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

### LIBRARY

Structured offline knowledge, searchable across sections: `RAVEN` · `RADIO` · `NAVIGATION` · `COMMS` · `CYBER` · `COMPUTING` · `EMERGENCY` · `MEDICAL` · `REPAIR` · `SURVIVAL` · `TRAVEL` · `GENERAL`. Supports local articles, operator-selected documentation and companion Kiwix/ZIM collections. Bootstrap supported open-source sources with `bash scripts/bootstrap-knowledge.sh` — see [Offline Knowledge Sources](docs/KNOWLEDGE-SOURCES.md).

### RVN-01

Live system-health view: CPU/temperature/memory/storage, power and throttle state, USB and attached hardware, GPS/SDR/mesh/audio readiness, Bluetooth and network state, SSH/mDNS connectivity, and FIELD//OS service status.

## Quick start (development)

Requires Python 3.11+.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
fieldos --windowed
```

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
fieldos --windowed
```

Drop `--windowed` to run full-screen, as it runs on RVN-01. Run the test suite with `python -m unittest discover -s tests`.

## RVN-01 install

On Raspberry Pi OS / Debian ARM64:

```bash
git clone https://github.com/logsexe/Project-RAV3N.git
cd Project-RAV3N
sudo bash scripts/install-rvn01.sh "$USER"
```

See [scripts/](scripts/) for appliance-mode (boot-to-FIELD//OS) install/removal and hardware-check helpers, and [deploy/](deploy/) for the corresponding systemd units.

## Runtime data

```text
~/.fieldos/
├─ state.json
├─ exports/
└─ sessions/<OPERATION-ID>/
   ├─ metadata.json
   ├─ notes/  commands/  scans/  captures/  evidence/  exports/
```

Override the root with `FIELDOS_DATA_DIR`; index local reference-repo checkouts with `FIELDOS_KNOWLEDGE_PATHS`.

## Hardware

Current platform baseline: Raspberry Pi 5 (8 GB), Active Cooler, 7-inch 800×480 touchscreen, local storage, powered USB expansion, Bluetooth, and optional GNSS / Meshtastic / RTL-SDR / audio modules.

See the [RVN-01 Hardware BOM](hardware/bom/RVN-01-BOM.md) for the current confirmed inventory and commissioning order.

## Current focus

1. Finish the FIELD//OS LIBRARY experience
2. Commission arriving hardware modules
3. Expand RVN-01 system-health telemetry
4. Refine appliance boot and recovery behaviour
5. Finalise the physical RVN-01 layout

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

## License

[Apache License 2.0](LICENSE)

---

**RAVEN // RVN-01 // FIELD//OS // OFFLINE FIELD COMPUTER**
