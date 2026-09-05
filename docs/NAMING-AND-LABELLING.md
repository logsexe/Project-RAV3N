# RAVEN Naming & Labelling Standard

## Primary designation

```text
RAVEN // RVN-01
FIELD OPERATIONS TERMINAL
HW REV A // FIELD//OS
```

## Hierarchy

- **Project:** PROJECT RAV3N
- **Platform:** RAVEN
- **Unit:** RVN-01
- **Role:** FIELD OPERATIONS TERMINAL
- **Software environment:** FIELD//OS
- **Hardware revision:** REV A

`RAV3N` is the project/brand styling. `RAVEN` is used for the platform designation and `RVN` for hardware identifiers.

## Module designations

| Designation | Module |
|---|---|
| RVN-M1 | Mesh / Meshtastic module |
| RVN-RF1 | RF / SDR module |
| RVN-GN1 | GNSS module |
| RVN-PW1 | Power module |
| RVN-IO1 | I/O module |
| RVN-LB1 | Hardware Lab module |

Module identifiers remain provisional until the hardware architecture is frozen.

## Panel labelling style

Prefer short functional labels and machine-readable hierarchy over decorative text.

```text
RVN-01 // FIELD OPERATIONS TERMINAL

SYS     NET     MESH     GNSS     RF
PWR     DATA    SERVICE  AUX      LAB

HW REV A
FIELD//OS
UNIT 001
```

## Status terminology

Use consistent status terms throughout software and physical labelling:

- READY
- ONLINE
- OFFLINE
- CONNECTED
- NOT PRESENT
- DEGRADED
- FAULT
- DEVELOPMENT

## Visual direction

Industrial field-equipment aesthetic: restrained, functional and technical. Avoid excessive fake warning labels or generic `CYBERDECK` branding. RAVEN identity should be obvious from typography, hierarchy, module designations and a subtle raven insignia.
