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
- [x] Session directory structure for notes/scans/captures/evidence/exports
- [x] Active operation shown in compact status bar
- [x] Operator playbook engine
- [x] Network Triage / Windows IR / Evidence Intake playbooks
- [x] Wireless Survey / RF Observation playbooks
- [x] Playbook step command staging into terminal

## FIELD//OS V0.5 — Offline knowledge and operator state

- [x] Persistent favourites
- [x] Persistent recent tools
- [x] Combined tool + knowledge global search
- [x] Bundled offline knowledge vault
- [x] Local documentation/repository indexer
- [x] SquidSec / BlueTeam-Tools / RedTeam-Tools local adapter via FIELDOS_KNOWLEDGE_PATHS
- [x] Knowledge entries can stage example commands into terminal
- [x] Operation ZIP export workflow
- [x] Compact Favourites / Recent / Knowledge views

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

## FIELD//OS V0.6+

- [ ] Theme configuration / low-light profiles
- [ ] Meshtastic adapter
- [ ] GNSS/gpsd adapter
- [ ] Real system telemetry
- [ ] Network interface manager
- [ ] Event timeline beyond notes
- [ ] Tool result normalisation into operation folders
- [ ] Command output capture to scans/captures/evidence
- [ ] Appliance-style startup profile
- [ ] ARM64 installation/bootstrap tooling
- [ ] Automated compatibility checks for Pi tool manifests

## V1 target

RAVEN should boot into a cohesive FIELD//OS environment with reliable keyboard navigation, offline knowledge, persistent operations, notes, playbooks, core cyber/network/DFIR tooling, hardware status, Meshtastic and GNSS integration, while retaining access to the underlying Linux environment for advanced work.
