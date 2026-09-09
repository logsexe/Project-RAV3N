# FIELD//OS V1.2 — Operator Interface

FIELD//OS V1.2 redesigns the RVN-01 terminal experience around a keyboard-first, 800×480 field interface inspired by the fast category and recipe navigation of SquidSec CyberDeck while retaining RAVEN's own operational model.

## Interface model

The primary dashboard is now an operator menu with live RVN-01 state alongside navigation. Core destinations are Dashboard, Tools, Playbooks, Operations, Assets, Evidence, Intel, Knowledge, Terminal, Hardware and Settings.

The UI keeps the existing FIELD//OS review-first execution model. Tool recipes are staged for operator review rather than executed automatically, and completed terminal commands continue to be captured under the active operation.

## V1.2 changes

- CyberDeck-inspired menu hierarchy and visual treatment.
- 800×480-first layout for the RVN-01 seven-inch display.
- Live operation, asset, evidence, network, GPS, mesh, thermal and isolation state on the dashboard.
- Dedicated Assets and Evidence views.
- Profile-aware tool library filtering.
- Global search extended to active-operation assets.
- Operator Settings view for profile and theme selection plus air-gap status.
- Simplified primary navigation: arrows, Enter, Esc and `/` search.
- F-keys remain available as fast-access shortcuts rather than being required for normal navigation.
- Air-gap status polling is cached to reduce repeated system-command execution on Raspberry Pi.
- `fieldos-check` now reports the package version dynamically and honours the configured FIELD//OS data root.

## Design principles

FIELD//OS remains a RAVEN interface, not a fork or visual clone of CyberDeck. The interface borrows the useful ideas of category-first navigation, command cookbook presentation and retro terminal clarity, then extends them with persistent operations, evidence, asset state, hardware telemetry, profiles and field-device integration.

Red-team and dual-use tooling remains explicitly review-first and intended only for systems the operator owns or is authorised to test.
