# RAVEN // RVN-01

**Portable Raspberry Pi 5 field computer running FIELD//OS.**

Project RAV3N is a rugged, offline-first field-computing platform for communications, navigation, receive-only RF, local networking, offline knowledge, operations and hardware telemetry. FIELD//OS presents those capabilities as dedicated applications on the RVN-01 7-inch display instead of exposing a conventional desktop.

> Development hardware. Use radio, network and security capabilities only where lawful and authorised.

## FIELD//OS

Current development priority: **V3 offline knowledge**, based on the efficient V2.9 graphical appliance stack.

The launcher is organised around operator tasks:

| App | Purpose |
| --- | --- |
| RADIO | Receive-only SDR, spectrum and tuning |
| NAVIGATION | Offline maps, GPS, waypoints and tracks |
| MESH | Meshtastic nodes and operator-controlled messaging |
| NETWORK | Local interfaces, devices and authorised diagnostics |
| OPS | Operations, evidence and timeline |
| LIBRARY | Categorised offline knowledge and local references |
| FILES | Local storage and operation files |
| TERMINAL | Explicit operator shell |
| RVN-01 | Hardware, storage, power and service status |

AI/ASSIST is deferred. The immediate goal is to make LIBRARY useful with reliable local articles, manuals, ZIM collections and official reference material.

Optional hardware degrades its own application only. Missing GPS, SDR or mesh hardware must never prevent FIELD//OS from starting.

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

See **[Module Installation Guide](docs/MODULE-INSTALL-GUIDE.md)** for RADIO/RTL-SDR, GPS, offline maps, Meshtastic, networking, offline knowledge, Bluetooth and appliance mode.

## Offline knowledge

FIELD//OS indexes bundled operator references plus operator-selected local documentation. A local tree categorises itself by folder:

```text
~/knowledge/
├── raven/
├── communications/
├── navigation/
├── radio/
├── cybersecurity/
├── computing/
├── emergency/
├── medical/
├── repair/
├── survival/
├── travel/
└── general/
```

Bootstrap the open-source documentation sources:

```bash
bash scripts/bootstrap-knowledge.sh
```

Then point FIELD//OS at the local trees you want indexed:

```bash
export FIELDOS_KNOWLEDGE_PATHS="$HOME/knowledge:$HOME/knowledge/_sources/raspberrypi-documentation/documentation:$HOME/knowledge/_sources/meshtastic-docs/docs"
```

Large ZIM/Kiwix collections remain companion content rather than being loaded into memory. Regulatory and medical references should retain visible revision dates and should not be redistributed unless their licence permits it.

See **[Offline Knowledge Sources](docs/KNOWLEDGE-SOURCES.md)** and the machine-readable catalogue at `config/knowledge/sources.yaml`.

## Performance profiling

```bash
bash scripts/rvn01-profile.sh
```

The profiler reports boot timing, memory, CPU, FIELD//OS footprint, services, storage and Pi thermal/throttle state without changing the host.

## Hardware baseline

See **[RVN-01 Hardware BOM](hardware/bom/RVN-01-BOM.md)** for the confirmed inventory and commissioning order.

## Repository

```text
fieldos/          FIELD//OS application and adapters
config/           tool, playbook and knowledge manifests
docs/             architecture, install and commissioning guides
deploy/           appliance/systemd configuration
scripts/          installation, rollback, knowledge and profiling tooling
hardware/         physical design/BOM material
assets/           branding and visual assets
tests/            automated tests
```

## Documentation

- [RVN-01 Hardware BOM](hardware/bom/RVN-01-BOM.md)
- [RVN-01 Commissioning](docs/RVN-01-COMMISSIONING.md)
- [Offline Knowledge Sources](docs/KNOWLEDGE-SOURCES.md)
- [Module Installation Guide](docs/MODULE-INSTALL-GUIDE.md)
- [FIELD//OS Architecture](docs/FIELD-OS-ARCHITECTURE.md)
- [Performance](docs/PERFORMANCE.md)
- [Roadmap](docs/ROADMAP.md)

---

`RAVEN // RVN-01 // FIELD//OS // OFFLINE FIELD COMPUTER`
