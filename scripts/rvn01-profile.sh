#!/usr/bin/env bash
set -u

echo 'RAVEN // RVN-01 // FIELD//OS PERFORMANCE PROFILE'
echo "timestamp: $(date -Is)"
echo

echo '== BOOT =='
systemd-analyze 2>/dev/null || true
systemd-analyze blame 2>/dev/null | head -20 || true
echo

echo '== MEMORY =='
free -h || true
echo

echo '== TOP CPU/RAM =='
ps -eo pid,comm,%cpu,%mem,rss --sort=-%cpu | head -15 || true
echo

echo '== FIELDOS =='
pgrep -af 'fieldos|qt_field_app' || true
for pid in $(pgrep -f 'fieldos|qt_field_app' 2>/dev/null | head -3); do
  ps -p "$pid" -o pid,etime,%cpu,%mem,rss,vsz,comm || true
done
echo

echo '== FAILED SERVICES =='
systemctl --failed --no-pager 2>/dev/null || true
echo

echo '== ENABLED SERVICES =='
systemctl list-unit-files --state=enabled --type=service --no-pager 2>/dev/null || true
echo

echo '== STORAGE =='
df -h / "$HOME" 2>/dev/null || true
echo

echo '== THERMAL =='
if command -v vcgencmd >/dev/null 2>&1; then
  vcgencmd measure_temp || true
  vcgencmd get_throttled || true
fi
