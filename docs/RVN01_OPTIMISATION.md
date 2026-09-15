# RVN-01 optimisation baseline

FIELD//OS is treated as an appliance. Optimisation must be measured on the physical RVN-01 rather than applying generic Raspberry Pi debloat scripts.

## Targets

- launcher renders immediately from cached/unknown state
- no GPS, mesh, SDR or network hardware probe blocks the UI thread
- one hardware service owns physical telemetry polling
- missing peripherals degrade individual apps, never FIELD//OS boot
- FIELD//OS restarts after an unexpected application failure
- minimise unnecessary microSD writes
- idle services are removed only after the RVN-01 audit proves they are unnecessary

## Audit first

Run:

```bash
bash scripts/rvn01-audit.sh | tee ~/rvn01-audit.txt
```

Capture the output before changing system services. In particular review boot time, enabled services, failed units, idle memory, CPU consumers and storage.

## Service deployment

`deploy/fieldos.service` is the reference systemd unit. Review its user and paths before installation. Do not enable it until `fieldos` runs correctly from the virtual environment.

## Debloat policy

Do not blindly remove packages or disable services. Candidates such as desktop components, Bluetooth, printing, discovery services and unused networking components must first be checked against the final RVN-01 hardware design. GPS, Meshtastic, SDR, audio, Wi-Fi and local networking are intentional capabilities and must not be accidentally removed.

## Storage policy

Operational evidence and explicit recordings are persistent. Disposable caches and temporary processing should use bounded cache locations or `/tmp`. Logs should be rotated rather than allowed to grow indefinitely.
