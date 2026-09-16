#!/usr/bin/env bash
set -euo pipefail

if [[ ${EUID} -ne 0 ]]; then
  echo 'Run with sudo: sudo bash scripts/install-appliance-mode.sh'
  exit 1
fi

PROJECT=/home/logs/Project-RAV3N
SERVICE_SRC="$PROJECT/deploy/fieldos-appliance.service"
SERVICE_DST=/etc/systemd/system/fieldos-appliance.service

[[ -f "$SERVICE_SRC" ]] || { echo "Missing $SERVICE_SRC"; exit 1; }
[[ -x "$PROJECT/.venv/bin/fieldos" ]] || { echo 'FIELD//OS venv entry point missing; install the project first.'; exit 1; }

install -m 0644 "$SERVICE_SRC" "$SERVICE_DST"
mkdir -p /home/logs/.fieldos
chown logs:logs /home/logs/.fieldos

# Conservative debloat: keep Bluetooth, NetworkManager, SSH, AppArmor,
# Avahi/mDNS, audio and the graphical stack. Remove only first-boot cloud
# provisioning and the optional VNC control helper from the steady-state path.
for unit in \
  cloud-config.service cloud-final.service cloud-init-local.service \
  cloud-init-main.service cloud-init-network.service \
  wayvnc-control.service; do
  systemctl disable --now "$unit" 2>/dev/null || true
done

# Explicitly preserve capabilities required for a headless RVN-01 workflow.
systemctl enable --now bluetooth.service 2>/dev/null || true
systemctl enable --now avahi-daemon.service 2>/dev/null || true
systemctl enable --now ssh.service 2>/dev/null || true

systemctl daemon-reload
systemctl enable fieldos-appliance.service

echo 'FIELD//OS appliance mode installed.'
echo 'Bluetooth: retained/enabled.'
echo 'Avahi/mDNS: retained/enabled for rvn-01.local access.'
echo 'SSH: retained/enabled.'
echo 'NetworkManager + AppArmor: untouched.'
echo 'LightDM/desktop: retained for the first appliance validation pass.'
echo 'Reboot only when ready: sudo reboot'
