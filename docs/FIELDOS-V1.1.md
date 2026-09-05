# FIELD//OS V1.1 — Operations, Profiles, Maps and Authentication

FIELD//OS V1.1 extends the RVN-01 software baseline with structured operational state rather than treating every tool result as isolated terminal output.

## Asset / Evidence Engine

`fieldos.engine.OperationsEngine` stores structured assets, evidence and events in `~/.fieldos/operations.db` (or below `FIELDOS_DATA_DIR`). Assets have stable `AS-...` IDs. Evidence ingestion copies the source into the active operation, records SHA-256, size, MIME type, timestamps and an optional asset association. Evidence receives a stable `EV-...` ID and can be re-verified later.

Examples:

```bash
fieldos-control asset add HOST 10.10.20.17 --label WORKSTATION-17
fieldos-control asset list
fieldos-control evidence ingest capture.pcap
fieldos-control evidence ingest memory.raw --asset AS-XXXXXXXX
fieldos-control evidence list
fieldos-control evidence verify EV-XXXXXXXX
fieldos-control timeline
```

F12 in the FIELD//OS TUI opens a read-only intelligence view showing the current operation's assets, evidence and recent timeline events.

## Profiles

Persistent profiles are `FIELD`, `BLUE`, `RED`, `FORENSICS`, `RF`, `AIRGAP` and `LOW POWER`. Each profile defines tool-category policy, network policy and hardware policy. AIRGAP is offline-only. LOW POWER marks reduced-hardware behaviour.

```bash
fieldos-control profile
fieldos-control profile FORENSICS
fieldos-control profile "LOW POWER"
```

F11 cycles the current profile in the TUI. Selecting the AIRGAP profile does not silently disconnect networking; actual isolation remains explicit.

## Air-gap mode

Actual radio/network isolation can terminate SSH and remote administration, so enforcement requires explicit confirmation:

```bash
fieldos-control airgap status
fieldos-control airgap on --confirm
fieldos-control airgap off --confirm
```

On Linux FIELD//OS uses available `nmcli` and `rfkill` controls to disable networking, Wi-Fi and Bluetooth. The active state is visible in the V1.1 status UI.

## Offline maps

`fieldos.maps.OfflineMapStore` supports local MBTiles packages plus separate overlays for operator waypoints and Meshtastic node positions. Place legally obtained OpenStreetMap-derived `.mbtiles` files in `~/.fieldos/maps/`.

```bash
fieldos-control maps list
fieldos-control waypoint add -37.8136 144.9631 "OBSERVATION POINT"
fieldos-control waypoint list
```

Waypoints can be linked to the active operation and automatically create timeline events. The map store already exposes tile retrieval so a later 800×480 TUI renderer can draw maps without changing the data model.

When using OpenStreetMap-derived data, retain the attribution required by the provider and OpenStreetMap licence terms.

## Operator authentication and encrypted storage

Authentication is optional. PINs are never stored directly; FIELD//OS stores a random salt and scrypt verifier. A removable key file can also be enrolled.

```bash
fieldos-control auth init-pin
fieldos-control auth status
fieldos-control auth verify
fieldos-control auth add-key /media/operator/RAVEN.key
```

The operator PIN can derive a separate 256-bit vault key. Encrypted evidence uses AES-256-GCM authenticated encryption and the `RVNVAULT1` artefact marker:

```bash
fieldos-control evidence ingest sensitive.bin --encrypt
fieldos-control evidence verify EV-XXXXXXXX --encrypted
```

Application-level vault encryption is an additional layer, not a replacement for full-disk encryption on the finished RVN-01.

## Design direction

The Operations Engine is deliberately separate from the Textual UI. Future adapters can parse Nmap, Zeek, YARA, GNSS, Meshtastic, RF and hardware observations into the same asset/evidence/event model. This allows the TUI, CLI and future APIs to operate over one consistent FIELD//OS core.
