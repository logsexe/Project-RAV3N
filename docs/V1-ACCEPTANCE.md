# RAVEN RVN-01 // V1 Acceptance

FIELD//OS V1.0 is the software baseline for RVN-01. This checklist separates software acceptance from physical hardware commissioning so the project does not claim hardware validation before the actual unit is assembled.

## Software baseline — complete

- [x] 800×480 keyboard-first interface
- [x] Tool libraries and command recipes
- [x] Full-screen command terminal with multiple sessions
- [x] Persistent terminal working directory via `cd`
- [x] Running-command interruption request
- [x] Persistent field operations / cases
- [x] Timestamped notes
- [x] Automatic command transcript capture
- [x] Evidence / captures / scans / commands / exports structure
- [x] Operation ZIP export
- [x] Operator playbooks
- [x] Favourites and recent tools
- [x] Offline knowledge and repository indexing
- [x] Global combined search
- [x] Real system telemetry fallback layer
- [x] Network-interface discovery
- [x] gpsd/gpspipe readiness detection
- [x] Meshtastic CLI / serial readiness detection
- [x] Low-light themes
- [x] Compatibility health check
- [x] Raspberry Pi / Debian installer
- [x] tty1 appliance service
- [x] Cross-platform CI configuration

## First Pi boot

Run:

```bash
fieldos-check
fieldos
```

Acceptance:

- FIELD//OS starts without a traceback.
- Interface is readable at 800×480.
- Keyboard navigation works without a mouse.
- F2 opens Terminal.
- F3 opens Operations.
- F4 shows live platform telemetry.
- F5 opens Notes.
- F9 opens Playbooks.
- F10 cycles themes.
- `cd` persists in the current terminal session.
- Completed commands create files under `~/.fieldos/sessions/<operation>/commands/`.
- Operation export creates a ZIP under `~/.fieldos/exports/`.

## Physical RVN-01 acceptance — pending hardware commissioning

- [ ] 7-inch touchscreen confirmed at intended 800×480 mode
- [ ] Keyboard stable in RVN-KB1 mount
- [ ] Keyboard USB routing does not interfere with closure or gasket
- [ ] Pi 5 and Active Cooler pass sustained thermal load
- [ ] M.2 HAT+ / storage stable under load
- [ ] USB hub stable with intended peripherals
- [ ] Power architecture supports peak Pi/peripheral load
- [ ] Battery telemetry integration finalised once power module is selected
- [ ] GNSS fix acquired and reported in FIELD//OS
- [ ] Meshtastic module detected and configured for the intended region
- [ ] Dedicated Wi-Fi adapter driver verified on ARM64
- [ ] RTL-SDR receive test passes without unacceptable internal interference
- [ ] Closed-case idle/load temperature test completed
- [ ] 2-hour field endurance test completed
- [ ] Appliance boot into FIELD//OS validated on tty1
- [ ] Clean shutdown / recovery behaviour validated

## Release rule

`FIELD//OS V1.0` may be treated as software-complete now. `RAVEN RVN-01 V1` should only be marked physically complete after every relevant hardware item above is tested on the assembled unit.
