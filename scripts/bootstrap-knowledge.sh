#!/usr/bin/env bash
set -euo pipefail

ROOT="${FIELDOS_KNOWLEDGE_ROOT:-$HOME/knowledge}"
SOURCES="$ROOT/_sources"
mkdir -p "$SOURCES" "$ROOT/raven" "$ROOT/communications" "$ROOT/navigation" "$ROOT/radio" "$ROOT/cybersecurity" "$ROOT/computing" "$ROOT/emergency" "$ROOT/medical" "$ROOT/repair" "$ROOT/survival" "$ROOT/travel" "$ROOT/general"

clone_or_update() {
  local url="$1"
  local dest="$2"
  if [[ -d "$dest/.git" ]]; then
    echo "UPDATE  $dest"
    git -C "$dest" pull --ff-only
  elif [[ -e "$dest" ]]; then
    echo "SKIP    $dest exists but is not a git checkout"
  else
    echo "CLONE   $url"
    git clone --depth 1 "$url" "$dest"
  fi
}

clone_or_update https://github.com/raspberrypi/documentation.git "$SOURCES/raspberrypi-documentation"
clone_or_update https://github.com/meshtastic/meshtastic.git "$SOURCES/meshtastic-docs"
clone_or_update https://github.com/mitre-attack/attack-stix-data.git "$SOURCES/mitre-attack-stix-data"

echo
echo 'FIELD//OS knowledge source bootstrap complete.'
echo "Root: $ROOT"
echo
echo 'Add these paths to FIELDOS_KNOWLEDGE_PATHS if you want FIELD//OS text indexing:'
echo "$SOURCES/raspberrypi-documentation/documentation"
echo "$SOURCES/meshtastic-docs/docs"
echo
echo 'MITRE ATT&CK is retained primarily as structured STIX data; do not index the entire JSON corpus as prose.'
echo 'Kiwix ZIMs and personal-use PDFs are intentionally not downloaded by this script.'
