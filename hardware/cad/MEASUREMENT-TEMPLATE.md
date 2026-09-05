# RVN-01 Mechanical Measurement Sheet

Record dimensions in millimetres where possible. Measure the physical component at least twice before committing final CAD.

> Current values below are **PROVISIONAL / ruler-measured** and must not be treated as final-print dimensions.

## Keyboard

User-supplied provisional measurements:

- Overall width / long side: **10.1** — unit requires confirmation; likely **inches**, which would be approximately **256.5 mm**
- Overall front-to-back depth: **3.8** — unit requires confirmation; likely **inches**, which would be approximately **96.5 mm**
- Body height excluding keycaps: **20–25 mm**, gradually increasing toward the rear
- Keycap height above body: approximately **12 mm**
- Approximate maximum total height: **32–37 mm**, depending on where body height was measured
- Front-edge height: TBD
- Rear-edge height: TBD
- USB connector location: TBD
- USB plug/cable projection when connected: TBD
- Corner radius: TBD
- Rubber feet positions/heights: TBD

### Important dimensional sanity check

A 65% keyboard cannot realistically be 101 × 38 mm. The reported `10.1` and `3.8` figures are mechanically plausible if they were read in **inches** rather than centimetres:

- 10.1 in = **256.54 mm**
- 3.8 in = **96.52 mm**

These converted dimensions are therefore useful for rough layout only until the units are confirmed and the keyboard is measured with calipers.

## Case lid

User-supplied provisional measurements:

- Usable lid width/depth: approximately **240 mm** — clarify whether this means 240 mm in one direction or approximately 240 × 240 mm usable area
- Lid floor to closing/sealing obstruction: approximately **30 mm**
- Lid taper from bottom to top: TBD
- Corner radii: TBD
- Hinge-side obstruction/keep-out: TBD
- Latch-side obstruction/keep-out: TBD
- Seal/gasket keep-out: TBD

## Flush cradle target

Initial prototype clearance target: **0.4–0.6 mm per side**, subject to printer/material calibration.

The cradle should be removable and serviceable. Do not permanently trap the keyboard or interfere with the case seal.

Because the keyboard's total height may exceed the nominal 30 mm lid clearance, the final mount must reference the actual keycap/closed-case geometry rather than simply recessing the keyboard body to the lid floor.

## Next measurements to prioritise

1. Confirm whether `10.1 × 3.8` is inches.
2. Measure the case lid usable **left-to-right width** separately from **hinge-to-front depth**.
3. Measure keyboard front-edge and rear-edge body heights separately.
4. Measure the keyboard USB connector position and cable protrusion.
5. Check closed-case clearance with the keyboard placed in its intended orientation using a small amount of removable putty/foam as a compression gauge if required.

## CAD confidence

- GREEN — manufacturer CAD/drawing or physically verified with suitable measuring tools
- AMBER — ruler measurement or published dimension; verify before final print
- RED — unknown / must measure
