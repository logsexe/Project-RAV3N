#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID} -ne 0 ]]; then
  echo 'Run with sudo: sudo bash scripts/remove-appliance-mode.sh'
  exit 1
fi

systemctl disable --now fieldos-appliance.service 2>/dev/null || true
rm -f /etc/systemd/system/fieldos-appliance.service

# Restore only services the appliance installer intentionally disabled.
for unit in \
  cloud-config.service cloud-final.service cloud-init-local.service \
  cloud-init-main.service cloud-init-network.service avahi-daemon.service \
  wayvnc-control.service; do
  systemctl enable "$unit" 2>/dev/null || true
done

# Bluetooth was never removed; explicitly preserve it during rollback too.
systemctl enable bluetooth.service 2>/dev/null || true
systemctl daemon-reload

echo 'FIELD//OS appliance service removed and previous helper services re-enabled where available.'
echo 'Bluetooth remains enabled.'
