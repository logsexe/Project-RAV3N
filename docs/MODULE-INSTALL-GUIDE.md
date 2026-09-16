# FIELD//OS Module Installation Guide

This guide commissions optional RVN-01 modules individually. FIELD//OS must continue to boot when any optional module is absent.

## Base FIELD//OS

```bash
cd ~/Project-RAV3N
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

Optional Python integrations:

```bash
python -m pip install -e '.[all-python]'
```

## RADIO // RTL-SDR

Packages:

```bash
sudo apt update
sudo apt install -y rtl-sdr
rtl_test -t
```

For live FFT support:

```bash
source ~/Project-RAV3N/.venv/bin/activate
python -m pip install -e '.[radio]'
```

FIELD//OS treats this module as receive-only. Connect the SDR only after the package/driver test succeeds.

## NAVIGATION // GPS / gpsd

```bash
sudo apt install -y gpsd gpsd-clients
sudo systemctl enable --now gpsd.socket
cgps -s
```

A receiver with no position solution is valid and should appear as `NO FIX`, not as a FIELD//OS failure.

## NAVIGATION // Offline maps

Install a companion viewer if desired:

```bash
sudo apt install -y qmapshack
```

Place FIELD//OS MBTiles packs under the configured local map directory. Keep maps on local storage so NAVIGATION remains useful without Internet access.

## MESH // Meshtastic

```bash
source ~/Project-RAV3N/.venv/bin/activate
python -m pip install -e '.[mesh]'
meshtastic --info
```

Connect the Meshtastic device over USB only after the CLI is installed. FIELD//OS does not transmit automatically.

## NETWORK

Core local diagnostics:

```bash
sudo apt install -y iproute2 dnsutils whois nmap
```

Optional packet tooling:

```bash
sudo apt install -y tcpdump tshark
```

Use active discovery only on networks and systems you own or are authorised to assess.

## LIBRARY // Offline knowledge

FIELD//OS has a built-in local knowledge index. Additional local documentation trees can be added with:

```bash
export FIELDOS_KNOWLEDGE_PATHS="$HOME/knowledge/manuals:$HOME/knowledge/reference"
```

For large offline reference collections, Kiwix/ZIM files can be used as companion content. Keep operator-authored Markdown/text references in local category directories for fast FIELD//OS search.

## ASSIST // Offline AI

The supported first adapter is a local Ollama endpoint. Install Ollama using its official Raspberry Pi/Linux instructions, then pull a small ARM-friendly model appropriate to available RAM. FIELD//OS does not download a model automatically.

After Ollama is installed:

```bash
ollama list
ollama serve
```

Configure FIELD//OS if the model name differs from the default:

```bash
export FIELDOS_AI_MODEL='<local-model-name>'
export FIELDOS_AI_URL='http://127.0.0.1:11434'
```

The AI adapter is local-only by default. It is an optional assistant, not an autonomous executor: it does not run terminal commands, transmit radio traffic, change network configuration, or modify evidence automatically.

## BLUETOOTH

Bluetooth is intentionally retained on RVN-01:

```bash
sudo systemctl enable --now bluetooth
bluetoothctl show
```

## Appliance mode

After the physical display is connected and graphical FIELD//OS has been validated:

```bash
cd ~/Project-RAV3N
sudo bash scripts/install-appliance-mode.sh
sudo reboot
```

Rollback:

```bash
cd ~/Project-RAV3N
sudo bash scripts/remove-appliance-mode.sh
sudo reboot
```

## Verification

```bash
systemctl --failed --no-pager
bluetoothctl show
ip address
bash scripts/rvn01-profile.sh
```

Missing optional hardware should degrade its own app only; it must not prevent FIELD//OS from launching.
