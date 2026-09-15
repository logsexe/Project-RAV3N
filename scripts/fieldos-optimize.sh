#!/usr/bin/env bash
set -Eeuo pipefail

# RAVEN // RVN-01 FIELD//OS optimiser
# Conservative, reversible appliance optimisation for Raspberry Pi OS.
# Does not remove packages, networking, SSH, Bluetooth, audio, GPS, Meshtastic,
# SDR support, graphics, or FIELD//OS data.

MODE="${1:---apply}"
STATE_ROOT="/var/lib/fieldos/optimisation"
STAMP="$(date +%Y%m%d-%H%M%S)"
RUN_DIR="$STATE_ROOT/$STAMP"
LATEST="$STATE_ROOT/latest"

log() { printf '[FIELD//OS] %s\n' "$*"; }
warn() { printf '[FIELD//OS] WARNING: %s\n' "$*" >&2; }

need_root() {
  if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
    exec sudo -- "$0" "$@"
  fi
}

unit_exists() {
  systemctl list-unit-files "$1" --no-legend 2>/dev/null | grep -q "^$1"
}

record_unit() {
  local unit="$1"
  if unit_exists "$unit"; then
    printf '%s|%s|%s\n' \
      "$unit" \
      "$(systemctl is-enabled "$unit" 2>/dev/null || true)" \
      "$(systemctl is-active "$unit" 2>/dev/null || true)" \
      >> "$RUN_DIR/units.tsv"
  fi
}

safe_disable() {
  local unit="$1"
  unit_exists "$unit" || return 0
  log "Disabling $unit"
  systemctl disable "$unit" >/dev/null 2>&1 || true
  systemctl stop "$unit" >/dev/null 2>&1 || true
}

safe_mask() {
  local unit="$1"
  unit_exists "$unit" || return 0
  log "Masking $unit"
  systemctl mask "$unit" >/dev/null 2>&1 || true
  systemctl stop "$unit" >/dev/null 2>&1 || true
}

audit() {
  local out="$1"
  {
    echo 'RAVEN // RVN-01 OPTIMISATION SNAPSHOT'
    echo '====================================='
    echo
    echo '[BOOT]'
    systemd-analyze 2>/dev/null || true
    systemd-analyze blame 2>/dev/null | head -20 || true
    echo
    echo '[MEMORY]'
    free -h || true
    echo
    echo '[FAILED SERVICES]'
    systemctl --failed --no-pager 2>/dev/null || true
    echo
    echo '[RUNNING SERVICES]'
    systemctl --type=service --state=running --no-pager 2>/dev/null || true
    echo
    echo '[THROTTLING]'
    command -v vcgencmd >/dev/null && vcgencmd get_throttled || true
    command -v vcgencmd >/dev/null && vcgencmd measure_temp || true
  } > "$out"
}

apply() {
  mkdir -p "$RUN_DIR"
  : > "$RUN_DIR/units.tsv"

  log "Creating baseline snapshot in $RUN_DIR"
  audit "$RUN_DIR/before.txt"
  systemctl list-unit-files --type=service --state=enabled --no-pager > "$RUN_DIR/enabled-before.txt" 2>/dev/null || true

  local units=(
    NetworkManager-wait-online.service
    docker.service
    docker.socket
    containerd.service
    cups.service
    rpcbind.service
    nfs-blkmap.service
    rp1-test.service
    glamor-test.service
  )
  for unit in "${units[@]}"; do record_unit "$unit"; done

  if [[ -e /etc/cloud/cloud-init.disabled ]]; then
    echo present > "$RUN_DIR/cloud-init-disabled-before"
  else
    echo absent > "$RUN_DIR/cloud-init-disabled-before"
  fi

  # NetworkManager itself remains enabled. Only remove the boot-time online wait.
  safe_mask NetworkManager-wait-online.service

  # Keep Docker installed but make it operator/on-demand only.
  safe_disable docker.service
  safe_disable docker.socket
  safe_disable containerd.service

  # Services not required by the current standalone RVN-01 role.
  safe_disable cups.service
  safe_disable rpcbind.service
  safe_disable nfs-blkmap.service

  # Completed provisioning should not run cloud-init on every appliance boot.
  mkdir -p /etc/cloud
  touch /etc/cloud/cloud-init.disabled

  # Raspberry Pi desktop/Xorg detection helpers are unnecessary for the
  # target FIELD//OS appliance path; packages remain installed for rollback.
  safe_disable rp1-test.service
  safe_disable glamor-test.service

  ln -sfn "$RUN_DIR" "$LATEST"
  audit "$RUN_DIR/after-apply.txt"

  log "Optimisation applied. No packages were removed."
  log "Preserved: NetworkManager, Wi-Fi, SSH, Bluetooth, audio, graphics, GPS, Meshtastic and SDR support."
  log "State/rollback data: $RUN_DIR"
  log "Reboot once, then run: sudo $0 --verify"
  log "Rollback any time with: sudo $0 --rollback"
}

rollback() {
  if [[ ! -L "$LATEST" && ! -d "$LATEST" ]]; then
    warn "No optimisation state found at $LATEST"
    exit 1
  fi
  local dir
  dir="$(readlink -f "$LATEST")"
  log "Rolling back from $dir"

  if [[ -f "$dir/units.tsv" ]]; then
    while IFS='|' read -r unit enabled active; do
      [[ -n "$unit" ]] || continue
      systemctl unmask "$unit" >/dev/null 2>&1 || true
      case "$enabled" in
        enabled|enabled-runtime|linked|linked-runtime|alias)
          systemctl enable "$unit" >/dev/null 2>&1 || true ;;
        disabled)
          systemctl disable "$unit" >/dev/null 2>&1 || true ;;
        masked|masked-runtime)
          systemctl mask "$unit" >/dev/null 2>&1 || true ;;
      esac
      if [[ "$active" == "active" ]]; then
        systemctl start "$unit" >/dev/null 2>&1 || true
      fi
    done < "$dir/units.tsv"
  fi

  if [[ -f "$dir/cloud-init-disabled-before" ]] && grep -qx absent "$dir/cloud-init-disabled-before"; then
    rm -f /etc/cloud/cloud-init.disabled
  fi

  log "Rollback complete. Reboot recommended."
}

verify() {
  mkdir -p "$STATE_ROOT"
  local out="$STATE_ROOT/verify-$STAMP.txt"
  audit "$out"
  cat "$out"
  echo
  log "Verification saved to $out"
  echo '[FIELD//OS] Expected appliance optimisation states:'
  for unit in NetworkManager-wait-online.service docker.service docker.socket containerd.service cups.service rpcbind.service nfs-blkmap.service rp1-test.service glamor-test.service; do
    if unit_exists "$unit"; then
      printf '  %-42s enabled=%-10s active=%s\n' "$unit" "$(systemctl is-enabled "$unit" 2>/dev/null || true)" "$(systemctl is-active "$unit" 2>/dev/null || true)"
    fi
  done
  printf '  %-42s %s\n' 'cloud-init' "$([[ -e /etc/cloud/cloud-init.disabled ]] && echo disabled || echo enabled)"
}

need_root "$@"
case "$MODE" in
  --apply) apply ;;
  --verify) verify ;;
  --rollback) rollback ;;
  *)
    echo "Usage: sudo $0 [--apply|--verify|--rollback]" >&2
    exit 2
    ;;
esac
