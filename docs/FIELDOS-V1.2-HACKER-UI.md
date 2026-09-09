# FIELD//OS V1.2 — Hacker UI refresh

This pass keeps the V1.2 operator workflow but shifts the presentation toward a darker phosphor terminal aesthetic inspired by classic hacker/cyberdeck interfaces.

## Terminal fix

The terminal input failure was caused by the V1.2 global `Enter` binding being marked as a priority binding. That intercepted the Enter key before Textual's `Input.Submitted` event could fire, so commands typed into the shell were never submitted.

V1.2 now reserves priority handling for navigation keys that must never be swallowed by a view. `Enter`, `Left`, and `Right` are non-priority so focused input widgets can submit commands and edit text normally. Up/Down remain priority to support menu navigation and terminal history.

## Visual changes

- black/green phosphor palette
- `ROOT://FIELDOS/...` breadcrumb language
- operator matrix dashboard
- ASCII bordered system panels
- `>_` selection cursor
- `READY` / `OFFLN` module state language
- tool views presented as module dossiers
- evidence presented as a vault
- assets presented as a registry
- terminal relabelled as shell
- explicit keyboard footer on every major view

The interface remains 800×480-first and keyboard-driven. Existing operation capture, evidence, profile, playbook and hardware integrations remain unchanged.
