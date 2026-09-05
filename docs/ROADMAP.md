# Project RAV3N Roadmap

## Phase 0 — Architecture & measurement

- [x] Name platform RAVEN / RVN-01
- [x] Define FIELD//OS concept
- [x] Select rugged case
- [x] Confirm keyboard physically fits case
- [ ] Measure keyboard precisely
- [ ] Measure usable lid geometry precisely
- [ ] Verify 7-inch display dimensions and connector locations
- [ ] Build component CAD reference library
- [x] Define RVN-KB1 keyboard retention concept
- [ ] Produce RVN-KB1 printable CAD
- [ ] Establish base-panel coordinate system

## FIELD//OS V0.1 — Operator shell prototype

- [x] Python package scaffold
- [x] Main dashboard
- [x] Keyboard navigation
- [x] Standard list-based module navigation
- [x] Categories
- [x] Tool manifest loader
- [x] Local manifest search
- [x] Mock telemetry adapter
- [x] Tool detail views
- [x] Installed-tool detection
- [x] Hierarchical left/right navigation

## FIELD//OS V0.2 — Operator console

- [x] Breadcrumb navigation
- [x] Active-pane visual state
- [x] Expanded multi-category core tool library
- [x] Rich tool metadata
- [x] Operator command recipes
- [x] Recipe-aware search
- [x] Manifest / installed-tool status bar
- [ ] Search knowledge sources and commands
- [ ] SquidSec adapter/indexer
- [ ] Session model
- [ ] Favourites and recent tools
- [ ] Theme configuration
- [ ] Safe command hand-off / copy workflow
- [ ] Playbook engine

## Hardware REV A

- [ ] Raspberry Pi 5 bench bring-up
- [ ] Active Cooler verification
- [ ] microSD OS image
- [ ] M.2 HAT+ / NVMe planning
- [ ] Display integration
- [ ] Keyboard integration
- [ ] USB distribution
- [ ] Power architecture
- [ ] Cooling / airflow design
- [ ] Meshtastic module selection
- [ ] GNSS selection
- [ ] Dedicated Wi-Fi interface selection
- [ ] RTL-SDR planning

## FIELD//OS V0.3+

- [ ] Meshtastic adapter
- [ ] GNSS/gpsd adapter
- [ ] real system telemetry
- [ ] network interface manager
- [ ] event timeline
- [ ] offline knowledge vault
- [ ] tool result normalisation
- [ ] session exports
- [ ] appliance-style startup profile

## V1 target

RAVEN should boot into a cohesive FIELD//OS environment with reliable keyboard navigation, offline knowledge, sessions, core cyber/network/DFIR tooling, hardware status, Meshtastic and GNSS integration, while retaining access to the underlying Linux environment for advanced work.
