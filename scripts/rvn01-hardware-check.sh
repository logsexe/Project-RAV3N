#!/usr/bin/env bash
set -u

section() { printf '\n== %s ==\n' "$1"; }
have() { command -v "$1" >/dev/null 2>&1; }

printf 'RAVEN // RVN-01 // HARDWARE COMMISSIONING CHECK\n'
printf 'timestamp: %s\n' "$(date -Is)"
printf 'host: %s\n' "$(hostname)"

section 'USB TOPOLOGY'
if have lsusb; then
  lsusb || true
  printf '\n-- tree --\n'
  lsusb -t || true
else
  echo 'lsusb unavailable (install usbutils)'
fi

section 'SERIAL DEVICES'
for pattern in /dev/ttyACM* /dev/ttyUSB* /dev/serial/by-id/*; do
  for dev in $pattern; do
    [[ -e "$dev" ]] && printf '%s -> %s\n' "$dev" "$(readlink -f "$dev" 2>/dev/null || echo "$dev")"
  done
done

section 'GNSS / GPSD'
if have gpspipe; then
  timeout 4 gpspipe -w 2>/dev/null | head -20 || true
else
  echo 'gpspipe unavailable'
fi
if have systemctl; then
  systemctl is-active gpsd.service 2>/dev/null || true
  systemctl is-active gpsd.socket 2>/dev/null || true
fi

section 'RTL-SDR'
if have rtl_test; then
  timeout 8 rtl_test -t 2>&1 | head -40 || true
else
  echo 'rtl_test unavailable'
fi

section 'AUDIO'
if have aplay; then
  aplay -l 2>/dev/null || true
else
  echo 'aplay unavailable'
fi

section 'BLUETOOTH'
if have bluetoothctl; then
  bluetoothctl show 2>/dev/null || true
else
  echo 'bluetoothctl unavailable'
fi

section 'NETWORK'
if have ip; then
  ip -brief link || true
  ip -brief address || true
fi

section 'STORAGE / POWER / THERMAL'
df -h / 2>/dev/null || true
if have vcgencmd; then
  vcgencmd measure_temp || true
  vcgencmd get_throttled || true
fi

section 'FIELD//OS'
if [[ -x "$HOME/Project-RAV3N/.venv/bin/fieldos" ]]; then
  echo 'FIELD//OS venv: READY'
else
  echo 'FIELD//OS venv: NOT FOUND at ~/Project-RAV3N/.venv'
fi

cat <<'EOF'

RESULT GUIDE
- USB device present but module unavailable: install/configure userspace driver next.
- ttyACM/ttyUSB alone does NOT prove Meshtastic; identify by USB ID/by-id path first.
- GPS READY requires gpsd TPV data with mode >= 2, not merely a serial port.
- SDR commissioning remains receive-only.
- Meshtastic transmission remains explicit operator action.
EOF
