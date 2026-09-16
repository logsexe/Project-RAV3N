# RVN-01 Hardware BOM

Status values: `OWNED`, `ORDERED`, `PLANNED`, `TBD`.

This is the source of truth for RVN-01 hardware. Items are only marked `ORDERED` or `OWNED` when confirmed by the operator.

| Subsystem | Component | Status | Notes |
|---|---|---|---|
| Enclosure | Tactix Tough Case — Medium | OWNED | Keyboard physical fit confirmed |
| Compute | Raspberry Pi 5 — 8 GB | ORDERED | Core RVN-01 compute node |
| Cooling | Raspberry Pi Active Cooler | ORDERED/OWNED | Pi-specific cooling |
| Storage | Patriot EP 256 GB microSDXC | OWNED | Initial system storage |
| Storage | Raspberry Pi M.2 HAT+ | ORDERED/OWNED | NVMe device TBD; PCIe resource must be considered if AI accelerator is added |
| Display | Freenove 7-inch touchscreen | OWNED | 800×480 FIELD//OS target display |
| Input | 65% wired mechanical keyboard | OWNED | Exact dimensions pending |
| USB | Anker 4-port USB 3.0 data hub | OWNED | Unpowered/data hub; low-power peripherals only |
| USB | JESWO powered 7-port USB 3.0 hub | ORDERED | Primary powered peripheral distribution hub |
| Field instrument | Flipper Zero | OWNED | Removable field instrument |
| Comms | Heltec WiFi LoRa 32 V4/V3 development board + antenna — 915 MHz | ORDERED | Meshtastic / AU 915 MHz field mesh; Wi-Fi + Bluetooth capable |
| Comms | Hepzest 915 MHz LoRa antenna kit, 5 dBi SMA male + SMA female leads | ORDERED | Antenna set for Meshtastic/LoRa integration |
| Navigation | Core Electronics USB GPS Receiver — TEL0137 | ORDERED | Primary USB GNSS candidate |
| Navigation | Geekstory VK-162 G-Mouse USB GPS receiver | ORDERED | Secondary/spare USB GNSS candidate; Linux/Raspberry Pi commissioning required |
| RF | Nooelec NESDR SMArt v5 RTL-SDR bundle | ORDERED | 100 kHz–1.75 GHz-class receive-side SDR; bundled antennas |
| RF | Nooelec Flamingo FM broadcast-bandstop filter | ORDERED | FM broadcast rejection ahead of SDR where required |
| RF | Bingfu 30 cm RG316 SMA male → SMA female bulkhead extension | ORDERED | Top-panel RF feed-through |
| Audio | Pimoroni Picade Max USB Audio — PIM742 | ORDERED | USB stereo audio + speaker amplifier |
| Audio | 3-inch 4 Ω 3 W speakers — ADA1314 | ORDERED | Qty 2; stereo pair for internal audio |
| Audio | 24 AWG light-duty figure-8 speaker cable — CE06933 | ORDERED | Qty 3 m; internal speaker wiring |
| Network | Dedicated Wi-Fi adapter | TBD | Built-in wlan0 remains management interface; dedicated adapter only if later required |
| AI | Raspberry Pi AI HAT+ 2 | PLANNED | Candidate for local ASSIST/offline AI; PCIe conflict/architecture with M.2 HAT+ must be resolved before purchase/integration |
| Power | USB-C PD battery/power system | TBD | Select after bench power measurements with SDR/GNSS/LoRa/audio load |
| Controller | RP2040/RP2350 system controller | PLANNED | Power/buttons/fans/LEDs/watchdog later |

## Confirmed incoming capability set

The currently ordered hardware unlocks the following FIELD//OS commissioning tracks:

- **RADIO** — NESDR SMArt v5 + Flamingo FM + SMA bulkhead
- **NAVIGATION** — two independent USB GNSS receivers available for comparison/backup
- **MESH** — Heltec 915 MHz LoRa/Meshtastic node + external antenna set
- **AUDIO** — Picade Max + stereo 3 W speakers
- **USB POWER/DATA** — powered 7-port hub for SDR, GNSS, LoRa and audio peripherals

## Next commissioning order

1. Powered USB hub — verify stable Pi enumeration and power behaviour.
2. GNSS — identify both receivers with `lsusb`, select primary, configure gpsd and confirm a TPV fix.
3. SDR — identify NESDR, install/test RTL-SDR userspace stack, verify receive-only FFT in FIELD//OS.
4. FM filter + SMA bulkhead — bench-test before permanent panel mounting.
5. Heltec — flash/configure Meshtastic, identify serial device, verify receive/node state before enabling operator-controlled TX.
6. Audio — enumerate Picade Max USB audio, wire speakers, verify left/right output and safe volume.
7. Mechanical integration — only after all modules pass bench commissioning.
8. AI accelerator — resolve Pi PCIe/storage architecture before buying/installing AI HAT+ 2.

## Mechanical standards

- Raspberry Pi mounting: M2.5 where required by official hardware
- Printed chassis/modules: prefer M3 fasteners with heat-set inserts
- Prototype material: PLA
- General/final material: PETG or ASA as appropriate
- Flexible parts: TPU

## Design rule

Do not finalise printed geometry from retailer dimensions alone. Physical measurements and manufacturer CAD/drawings take precedence.
