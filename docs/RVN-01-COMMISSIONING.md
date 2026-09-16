# RVN-01 Hardware Commissioning

This is the bench workflow for bringing newly purchased RVN-01 modules online before permanent case integration.

## Rule

**BENCH -> IDENTIFY -> DRIVER -> TEST -> FIELD//OS -> MOUNT**

Do not permanently mount a new device until it enumerates reliably, survives a reboot, and FIELD//OS reports a truthful state.

## Headless workflow from Windows PowerShell

Connect to RVN-01:

```powershell
ssh logs@rvn-01.local
```

Update to the latest `main`:

```bash
cd ~/Project-RAV3N
git fetch origin --prune
git switch main
git pull --ff-only
```

Run the complete read-only commissioning snapshot:

```bash
bash scripts/rvn01-hardware-check.sh | tee ~/rvn01-hardware-check.txt
```

Copy the result back to Windows if required:

```powershell
scp logs@rvn-01.local:~/rvn01-hardware-check.txt "$HOME\Downloads\rvn01-hardware-check.txt"
```

## Commissioning order

### 1. Powered USB hub

Connect only the powered hub to the Pi first.

Run:

```bash
lsusb
lsusb -t
vcgencmd get_throttled
```

Pass criteria:
- USB controller/hub enumerates consistently
- no unexpected disconnect/reconnect loop
- `get_throttled=0x0` under normal idle conditions

### 2. USB GNSS receivers

Test each GPS receiver separately before deciding which becomes the primary RVN-01 GNSS source.

Capture:

```bash
lsusb
ls -l /dev/ttyACM* /dev/ttyUSB* /dev/serial/by-id/* 2>/dev/null
```

Then configure `gpsd` against the stable `/dev/serial/by-id/...` path when available.

Pass criteria:
- stable USB identity
- stable serial path
- gpsd starts without errors
- `gpspipe -w` returns TPV records
- an outdoor fix reaches TPV `mode` 2 or 3

### 3. Nooelec NESDR SMArt v5

With the SDR connected through the powered hub:

```bash
lsusb
rtl_test -t
```

Pass criteria:
- RTL2832-class USB device detected
- `rtl_test` opens the tuner successfully
- no kernel DVB driver conflict
- FIELD//OS RADIO can acquire receive-only FFT data

The Flamingo FM filter and SMA bulkhead should be inserted only after the bare SDR path is known-good.

RF chain:

```text
ANTENNA -> FLAMINGO FM -> SMA BULKHEAD -> NESDR SMArt v5 -> POWERED USB HUB -> PI 5
```

### 4. Heltec 915 MHz Meshtastic node

Connect the Heltec over a known data-capable USB cable.

Identify it before assigning a serial path:

```bash
lsusb
ls -l /dev/ttyACM* /dev/ttyUSB* /dev/serial/by-id/* 2>/dev/null
```

Pass criteria:
- board enumerates consistently
- stable serial by-id path where available
- Meshtastic CLI can query device information
- FIELD//OS reports the node only after positive Meshtastic identification
- transmission remains explicit operator action

### 5. Picade Max USB Audio + speakers

Connect the Picade Max over USB before wiring permanent speaker runs.

```bash
aplay -l
```

After the device is visible, wire the two 4 ohm / 3 W speakers with the 24 AWG figure-8 cable. Keep conductor polarity consistent between channels.

Pass criteria:
- USB audio device enumerates
- left and right output verified
- no clipping at intended FIELD//OS operating volume
- speaker wiring remains cool and secure

### 6. Full powered-hub load test

After every individual module passes, connect:
- NESDR
- primary GPS
- Heltec
- Picade Max

Then run:

```bash
bash scripts/rvn01-hardware-check.sh
vcgencmd get_throttled
```

Leave the system running for at least 15 minutes while exercising SDR receive, GPS and audio.

Pass criteria:
- no USB resets
- no under-voltage/throttling flag
- no disappearing serial devices
- normal CPU temperature
- FIELD//OS remains responsive

## Mechanical integration gate

Only after the full load test passes should the hub, SDR, bulkhead, GPS, Heltec and audio hardware be fixed into the enclosure.

This keeps wiring and mounting reversible while the hardware stack is still being validated.
