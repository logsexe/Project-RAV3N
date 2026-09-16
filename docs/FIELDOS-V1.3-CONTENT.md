# FIELD//OS V1.3 — Tool and Playbook Expansion

FIELD//OS V1.3 begins the full operational-content build-out for RVN-01.

## Modular catalogues

FIELD//OS now loads every YAML manifest under `config/tools/` and `config/playbooks/`. Tool and playbook IDs are deduplicated, allowing each operational category to grow independently without turning the original `core.yaml` files into monoliths.

## Expanded tool coverage

The catalogue now extends BLUE, RED, OSINT, NETWORK, FORENSICS, FIELD, COMMS, HARDWARE, RF and UTILITIES with additional host-audit, container, SBOM, Linux IR, filesystem forensics, carving, DNS, local-network discovery, public-domain enrichment, authorised web-validation, TLS, microcontroller, hardware-debug, Raspberry Pi and SDR utilities.

Commands remain operator-staged. Entries marked `authorised_use_only` are intended only for systems, networks and selectors the operator owns or is explicitly authorised to assess.

## Expanded playbook coverage

The V1.3 catalogue now covers network triage and baselining, DNS triage, authorised service inventory, PCAP triage, Windows and Linux incident response, malware static triage, container security review, evidence intake, disk-image triage, memory triage, firmware analysis, document metadata triage, public-selector/domain OSINT, RVN-01 readiness, Meshtastic, GNSS, USB/serial intake, Raspberry Pi hardware checks, RTL-SDR receive-only observation, authorised web/TLS validation and owned-domain attack-surface inventory.

The execution model remains review-first: playbook command steps are staged into the FIELD//OS terminal for operator review rather than autonomously executed.
