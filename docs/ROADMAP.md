# Project RAV3N Roadmap

## Software baseline — done

FIELD//OS is a PySide6 (Qt) full-screen appliance shell with nine surfaces, offline-first throughout: missing hardware reports `NOT PRESENT` rather than failing anything.

- [x] RADIO — receive-only SDR spectrum/waterfall, tune preview, live RTL-SDR FFT when a device is attached
- [x] NAVIGATION — offline MBTiles rendering, live GNSS overlay, waypoints with distance/bearing from the current fix, GPX import/export (interoperable with QMapShack, Garmin, OsmAnd)
- [x] MESH — Meshtastic node list, persistent connection, operator-controlled send/receive messaging logged into OPS
- [x] NETWORK — local interface and ARP/ND neighbour listing (passive, read-only)
- [x] OPS — assets, evidence, timeline and notes via `OperationsEngine`; operation switching, export to ZIP; terminal command transcripts captured automatically
- [x] LIBRARY — categorised offline knowledge search, Kiwix/ZIM companion support
- [x] FILES — read-only local storage browser
- [x] TERMINAL — persistent working directory, command history recall, output captured into the active operation
- [x] RVN-01 — live system/power/hardware/USB/network/service health
- [x] Cross-platform CI (Python 3.11 & 3.12, full test suite) and an installable `fieldos` console entry point

## Next — off-grid capability

RAV3N is being built for two overlapping audiences — security professionals doing authorised field work, and off-grid operators who need comms and navigation without infrastructure. See [Responsible use](../README.md#responsible-use) in the README before working on anything in this section.

- [x] NETWORK Wi-Fi scan (nearby SSID/BSSID/channel/signal via the built-in `wlan0`, plus a monitor-mode capability check) — explicit-action only, since this sends 802.11 probe requests and is not passive
- [ ] Select a dedicated Wi-Fi adapter for **passive** wireless recon (monitor mode; MediaTek MT7612U-class chipset preferred for mainline kernel support). No injection/attack tooling is planned at this stage.
- [ ] Wire real monitor-mode packet capture (AP/client enumeration, signal mapping) once that adapter exists — the current NETWORK Wi-Fi scan only covers the active-scan case above
- [ ] Establish a measured power budget across SDR + LoRa + dual GNSS + Wi-Fi + display before finalising the battery system — see [Hardware REV A](#hardware-rev-a--physical-commissioning)
- [ ] AI/ASSIST — `fieldos/offline_ai.py` (local Ollama adapter) is implemented but has no UI surface yet

## Hardware REV A — physical commissioning

- [ ] Raspberry Pi 5 bench bring-up
- [ ] Active Cooler verification
- [ ] microSD OS image and burn-in
- [ ] M.2 HAT+ / NVMe validation
- [ ] Display integration and 800×480 validation
- [ ] Keyboard integration / RVN-KB1 prototype
- [ ] USB distribution validation
- [ ] Power architecture and battery selection (blocked on the power budget above)
- [ ] Cooling / airflow validation
- [ ] Meshtastic module selection and AU-region validation
- [ ] GNSS module selection and fix testing
- [ ] Dedicated Wi-Fi interface selection and ARM64 driver testing
- [ ] RTL-SDR integration and noise testing
- [ ] Closed-case thermal test
- [ ] Field endurance test

See the [RVN-01 Hardware BOM](../hardware/bom/RVN-01-BOM.md) for the current confirmed inventory.

## Later — project maturity

Deferred deliberately until there's an active outside contributor to design for: CONTRIBUTING guide, issue templates, `SECURITY.md`, code of conduct.

## V1 acceptance target

RAVEN V1 is complete when the physical RVN-01 hardware has been commissioned against the software baseline above: the unit boots into FIELD//OS, the 7-inch display and keyboard are reliable, power and cooling are validated, and the installed GNSS/Meshtastic/network/RF modules report correctly through the hardware adapters.
