# RAVEN // RVN-01

**Portable Raspberry Pi 5 field computer running FIELD//OS.**

Project RAV3N is a rugged, offline-first field-computing platform for communications, navigation, receive-only RF, local networking, offline knowledge, operations and hardware telemetry. FIELD//OS presents those capabilities as dedicated applications on the RVN-01 7-inch display instead of exposing a conventional desktop.

> Development hardware. Use radio, network and security capabilities only where lawful and authorised.

## FIELD//OS

Current development line: **V3 knowledge / ASSIST preview**, based on the efficient V2.9 graphical appliance stack.

The launcher is organised around operator tasks:

| App | Purpose |
| --- | --- |
| RADIO | Receive-only SDR, spectrum and tuning |
| NAVIGATION | Offline maps, GPS, waypoints and tracks |
| MESH | Meshtastic nodes and operator-controlled messaging |
| NETWORK | Local interfaces, devices and authorised diagnostics |
| OPS | Operations, evidence and timeline |
| LIBRARY | Categorised offline knowledge and local references |
| ASSIST | Optional local AI using operator-controlled inference |
| FILES | Local storage and operation files |
| TERMINAL | Explicit operator shell |
| RVN-01 | Hardware, storage, power and service status |

Optional hardware degrades its own application only. Missing GPS, SDR, mesh or AI must never prevent FIELD//OS from starting.

## Core principles

- **Offline first** — maps, knowledge, operations and core UI remain useful without Internet access.
- **App oriented** — underlying Linux utilities are capabilities behind FIELD//OS applications.
- **Operator controlled** — no autonomous radio transmission, network scanning or shell execution.
- **Hardware tolerant** — peripherals can be connected, removed or unavailable without breaking the launcher.
- **Efficient** — expensive SDR/map work is demand-driven rather than continuously polling in the background.
- **Recoverable** — Raspberry Pi OS, SSH and rollback tooling remain available underneath the appliance.
- **Bluetooth retained** — Bluetooth is an intentional RVN-01 capability.

## Quick install // RVN-01

Raspberry Pi OS 64-bit and Python 3.11+ are expected.

```bash
git clone https://github.com/logsexe/Project-RAV3N.git
cd Project-RAV3N
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

Run tests:

```bash
python -m unittest discover -s tests -v
```

Start FIELD//OS from an active graphical session:

```bash
fieldos
```

For appliance deployment after the physical display is validated:

```bash
sudo bash scripts/install-appliance-mode.sh
sudo reboot
```

Rollback:

```bash
sudo bash scripts/remove-appliance-mode.sh
sudo reboot
```

## Optional modules

Do not bulk-install every integration. Commission only the modules fitted to your RVN-01.

See **[Module Installation Guide](docs/MODULE-INSTALL-GUIDE.md)** for RADIO/RTL-SDR, GPS, offline maps, Meshtastic, networking, offline knowledge, local AI, Bluetooth and appliance mode.

## Offline knowledge

FIELD//OS indexes bundled references and operator-selected local documentation. A local tree can categorise itself by folder:

```text
~/knowledge/
├── medical/
├── navigation/
├── radio/
├── communications/
├── repair/
├── survival/
├── computing/
├── networking/
├── manuals/
└── raven/
```

```bash
export FIELDOS_KNOWLEDGE_PATHS="$HOME/knowledge"
```

The index supports category listing/filtering, search and compact retrieval context. Large ZIM/Kiwix collections can remain companion content rather than being loaded into memory.

See **[Knowledge + AI](docs/KNOWLEDGE-AND-AI.md)**.

## Offline AI // ASSIST

FIELD//OS now includes the backend for an optional local AI assistant. The first adapter targets a local Ollama-compatible endpoint and defaults to loopback. It does not execute generated commands or perform hardware actions.

```bash
export FIELDOS_AI_URL='http://127.0.0.1:11434'
export FIELDOS_AI_MODEL='qwen2.5:1.5b'
```

Model installation is deliberately separate from FIELD//OS. A small quantised model should be benchmarked on the physical Pi 5 before selecting the permanent RVN-01 model.

## Performance profiling

```bash
bash scripts/rvn01-profile.sh
```

The profiler reports boot timing, memory, CPU, FIELD//OS footprint, services, storage and Pi thermal/throttle state without changing the host.

## Hardware baseline

- Raspberry Pi 5 8 GB
- Raspberry Pi Active Cooler
- Raspberry Pi M.2 HAT+
- 7-inch 800×480 touchscreen
- powered/expandable USB infrastructure
- 256 GB local storage baseline
- keyboard
- Bluetooth retained
- optional GNSS, Meshtastic and RTL-SDR modules

## Repository

```text
fieldos/          FIELD//OS application and adapters
config/           tool, playbook and knowledge manifests
docs/             architecture, install and commissioning guides
deploy/           appliance/systemd configuration
scripts/          installation, rollback and profiling
hardware/         physical design/BOM material
assets/           branding and visual assets
tests/            automated tests
```

## Documentation

- [Module Installation Guide](docs/MODULE-INSTALL-GUIDE.md)
- [Knowledge + AI](docs/KNOWLEDGE-AND-AI.md)
- [FIELD//OS Architecture](docs/FIELD-OS-ARCHITECTURE.md)
- [Performance](docs/PERFORMANCE.md)
- [Roadmap](docs/ROADMAP.md)

---

`RAVEN // RVN-01 // FIELD//OS // OFFLINE FIELD COMPUTER`
