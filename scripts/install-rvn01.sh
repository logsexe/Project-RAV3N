#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run with sudo: sudo ./scripts/install-rvn01.sh <operator-user>"
  exit 1
fi

OPERATOR_USER="${1:-${SUDO_USER:-pi}}"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET_DIR="/opt/fieldos"

if ! id "${OPERATOR_USER}" >/dev/null 2>&1; then
  echo "Operator user '${OPERATOR_USER}' does not exist."
  exit 1
fi

echo "RAVEN // FIELD//OS V1.0 // INSTALL"
echo "Operator: ${OPERATOR_USER}"
echo "Source:   ${SOURCE_DIR}"
echo "Target:   ${TARGET_DIR}"

apt-get update
apt-get install -y python3 python3-venv python3-pip git

mkdir -p "${TARGET_DIR}"
rsync -a --delete --exclude '.git' --exclude '.venv' "${SOURCE_DIR}/" "${TARGET_DIR}/"
python3 -m venv "${TARGET_DIR}/.venv"
"${TARGET_DIR}/.venv/bin/pip" install --upgrade pip
"${TARGET_DIR}/.venv/bin/pip" install -e "${TARGET_DIR}"

mkdir -p "/home/${OPERATOR_USER}/.fieldos"
chown -R "${OPERATOR_USER}:${OPERATOR_USER}" "/home/${OPERATOR_USER}/.fieldos"
chown -R root:root "${TARGET_DIR}"

install -m 0644 "${TARGET_DIR}/deploy/fieldos@.service" /etc/systemd/system/fieldos@.service
systemctl daemon-reload

echo
echo "Core install complete."
echo "Run health check: ${TARGET_DIR}/.venv/bin/fieldos-check"
echo "Enable appliance boot when ready:"
echo "  sudo systemctl disable getty@tty1.service"
echo "  sudo systemctl enable fieldos@${OPERATOR_USER}.service"
echo "  sudo systemctl start fieldos@${OPERATOR_USER}.service"
echo
echo "Optional hardware packages are deliberately not installed automatically."
echo "Install gpsd, Meshtastic, SDR and security tooling only as each RVN module is commissioned."
