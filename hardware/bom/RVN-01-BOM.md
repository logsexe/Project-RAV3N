# RVN-01 Hardware BOM

Status values: `OWNED`, `ORDERED`, `PLANNED`, `TBD`.

| Subsystem | Component | Status | Notes |
|---|---|---|---|
| Enclosure | Tactix Tough Case — Medium | OWNED | Keyboard physical fit confirmed |
| Compute | Raspberry Pi 5 — 8 GB | ORDERED | Awaiting arrival |
| Cooling | Raspberry Pi Active Cooler | ORDERED/OWNED | Pi-specific cooling |
| Storage | Patriot EP 256 GB microSDXC | OWNED | Initial system storage |
| Storage | Raspberry Pi M.2 HAT+ | ORDERED/OWNED | NVMe device TBD |
| Display | Freenove 7-inch touchscreen | OWNED | Exact unit ports/dimensions to verify |
| Input | 65% wired mechanical keyboard | OWNED | Exact dimensions pending |
| USB | Anker 4-port USB 3.0 data hub | OWNED | Unpowered/data hub; low-power peripherals only |
| Field instrument | Flipper Zero | OWNED | Removable dock planned |
| Comms | Meshtastic node | TBD | AU-compatible radio/configuration required |
| Navigation | GNSS receiver | TBD | USB/UART options to evaluate |
| RF | RTL-SDR | PLANNED | Receive-side RF capability |
| Network | Dedicated Wi-Fi adapter | TBD | Linux/ARM64 support important |
| Power | USB-C PD battery/power system | TBD | Select after bench power measurements |
| Controller | RP2040/RP2350 system controller | PLANNED | Power/buttons/fans/LEDs/watchdog later |

## Mechanical standards

- Raspberry Pi mounting: M2.5 where required by official hardware
- Printed chassis/modules: prefer M3 fasteners with heat-set inserts
- Prototype material: PLA
- General/final material: PETG or ASA as appropriate
- Flexible parts: TPU

## Design rule

Do not finalise printed geometry from retailer dimensions alone. Physical measurements and manufacturer CAD/drawings take precedence.
