#!/usr/bin/env bash
set -u

printf '%s\n' 'RAVEN // RVN-01 OPTIMISATION AUDIT'
printf '%s\n' '================================='
printf '\n[BOOT]\n'
systemd-analyze 2>/dev/null || true
systemd-analyze blame 2>/dev/null | head -20 || true

printf '\n[MEMORY]\n'
free -h || true

printf '\n[CPU / PROCESSES]\n'
ps -eo pid,comm,%cpu,%mem --sort=-%cpu | head -20 || true

printf '\n[ENABLED SERVICES]\n'
systemctl list-unit-files --type=service --state=enabled --no-pager 2>/dev/null || true

printf '\n[FAILED SERVICES]\n'
systemctl --failed --no-pager 2>/dev/null || true

printf '\n[STORAGE]\n'
df -h / /home 2>/dev/null || df -h / || true

printf '\n[FIELD//OS]\n'
command -v fieldos || true
python3 --version || true
printf '\nAudit is read-only. Review results before disabling or removing services.\n'
