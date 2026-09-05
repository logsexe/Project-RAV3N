# Project RAV3N Roadmap

## Phase 0 — Architecture & measurement

- [x] Name platform RAVEN / RVN-01
- [x] Define FIELD//OS concept
- [x] Select rugged case
- [x] Confirm keyboard physically fits case
- [x] Define RVN-KB1 keyboard retention concept
- [ ] Measure keyboard precisely
- [ ] Measure usable lid geometry precisely
- [ ] Verify 7-inch display dimensions and connector locations
- [ ] Build component CAD reference library
- [ ] Produce RVN-KB1 printable CAD
- [ ] Establish base-panel coordinate system

## FIELD//OS V0.1 — Operator shell prototype

- [x] Python package scaffold
- [x] Main dashboard
- [x] Keyboard navigation
- [x] Categories and tool manifest loader
- [x] Local manifest search
- [x] Mock telemetry adapter
- [x] Tool detail views and installed-tool detection

## FIELD//OS V0.2 — Tool console

- [x] Expanded multi-category core tool library
- [x] Rich tool metadata
- [x] Operator command recipes
- [x] Recipe-aware search
- [x] Embedded local terminal
- [x] Independent terminal sessions
- [x] Command history and staged recipe workflow

## FIELD//OS V0.3 — 800x480 appliance UI

- [x] Full-screen progressive views
- [x] Compact one-line platform status
- [x] Full-screen terminal view
- [x] Context-first keyboard controls
- [x] Dedicated system-status view
- [x] 7-inch display-oriented layout

## FIELD//OS V0.4 — Field operations layer

- [x] Persistent operation/session model
- [x] Per-operation timestamped notes
- [x] Session directory structure
- [x] Active operation status
- [x] Operator playbook engine
- [x] Network Triage / Windows IR / Evidence Intake playbooks
- [x] Wireless Survey / RF Observation playbooks
- [x] Playbook command staging

## FIELD//OS V0.5 — Offline knowledge and operator state

- [x] Persistent favourites
- [x] Persistent recent tools
- [x] Combined tool + knowledge search
- [x] Bundled offline knowledge vault
- [x] Local documentation/repository indexer
- [x] SquidSec / BlueTeam-Tools / RedTeam-Tools local knowledge adapter
- [x] Knowledge command staging
- [x] Operation ZIP export workflow

## FIELD//OS V1.0 — RVN-01 software baseline

- [x] Real best-effort system telemetry
- [x] Network-interface discovery
- [x] GNSS/gpsd readiness adapter
- [x] Meshtastic readiness adapter
- [x] CPU temperature / storage / battery telemetry
- [x] Persistent terminal `cd` working directory
- [x] Running-command interrupt control
- [x] Automatic command transcript capture per operation
- [x] `commands/` operation artefact directory
- [x] Phosphor / Amber / Ice / Red / Monochrome themes
- [x] Host compatibility health-check command
- [x] ARM64 / Debian bootstrap installer
- [x] tty1 appliance-style systemd service
- [x] Linux + Windows CI
- [x] V1 software documentation

## Hardware REV A — physical commissioning

- [ ] Raspberry Pi 5 bench bring-up
- [ ] Active Cooler verification
- [ ] microSD OS image and burn-in
- [ ] M.2 HAT+ / NVMe validation
- [ ] Display integration and 800×480 validation
- [ ] Keyboard integration / RVN-KB1 prototype
- [ ] USB distribution validation
- [ ] Power architecture and battery selection
- [ ] Cooling / airflow validation
- [ ] Meshtastic module selection and AU-region validation
- [ ] GNSS module selection and fix testing
- [ ] Dedicated Wi-Fi interface selection and ARM64 driver testing
- [ ] RTL-SDR integration and noise testing
- [ ] Closed-case thermal test
- [ ] Field endurance test

## V1 acceptance target

FIELD//OS V1 software is feature-complete. RAVEN V1 is complete when the physical RVN-01 hardware has been commissioned against the software baseline: the unit boots into FIELD//OS, the 7-inch display and keyboard are reliable, power and cooling are validated, and the installed GNSS/Meshtastic/network/RF modules report correctly through the hardware adapters.
