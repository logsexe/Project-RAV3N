# RAVEN // RVN-01

**An open-source, off-grid field computer.**

RAVEN is a rugged Raspberry Pi 5 build running **FIELD//OS**, a self-contained operator environment for going somewhere with no infrastructure — no cell signal, no Wi-Fi, no power grid — and still having navigation, communications, RF awareness, local network diagnostics, and a case-management layer for whatever you're doing out there.

It's built for two overlapping audiences: **security professionals** who need a field kit for authorised on-site work, and **off-grid operators** — backcountry travel, disaster response, remote fieldwork — who need comms and navigation that don't depend on infrastructure being there. The common thread is the same in both cases: everything works with zero connectivity, and nothing here calls home.

## Responsible use

RAVEN bundles capabilities — wireless monitoring, network diagnostics, evidence handling — that are dual-use by nature, the same way Kismet, Wireshark or a Flipper Zero are. That's a deliberate design choice, not an oversight, and it comes with the same expectation those tools carry:

- **Only use radio, network and wireless-recon capabilities on systems and spectrum you own or are explicitly authorised to test or observe.**
- FIELD//OS defaults to passive/receive-only behaviour everywhere it can (RADIO is receive-only, MESH transmission is an explicit operator action) — that default is intentional and should be preserved in anything built on top of it.
- The maintainers provide this software for lawful, authorised use only and accept no responsibility for misuse. Know and follow the laws that apply to radio transmission, network monitoring and wireless testing in your jurisdiction.

## Scope

- **Offline-first**: every feature works without Internet access; optional hardware (GPS, SDR, mesh) enhances FIELD//OS but its absence must never prevent it from starting — missing modules report `NOT PRESENT` rather than failing.
- **Operator-focused appliance**: a single full-screen application with a fixed home-screen grid, not a conventional desktop.
- **Explicit control**: radio, network and shell actions are operator-initiated, never automatic.
- **Built to be replicated**: the goal is a BOM, build guide and codebase that another builder can follow end-to-end, not a one-off personal build.

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

Current platform baseline: Raspberry Pi 5 (8 GB), Active Cooler, 7-inch 800×480 touchscreen, local storage, powered USB expansion, Bluetooth, and optional GNSS / Meshtastic / RTL-SDR / audio modules. A dedicated monitor-mode-capable Wi-Fi adapter is planned but not yet selected — see Current focus.

See the [RVN-01 Hardware BOM](hardware/bom/RVN-01-BOM.md) for the current confirmed inventory and commissioning order.

## Current focus

1. Select and commission a dedicated Wi-Fi adapter for passive wireless recon (monitor mode, no injection/attack tooling planned at this stage), and build the FIELD//OS surface for it, gated through the existing operator-profile system
2. Establish a real, measured power budget across SDR/LoRa/GNSS/Wi-Fi/display before finalising the battery system — the single most safety-critical unresolved item for an off-grid device
3. Commission arriving hardware modules
4. Refine appliance boot and recovery behaviour
5. Finalise the physical RVN-01 layout
6. Keep the BOM, build guide and install docs accurate enough for another builder to follow end-to-end

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
