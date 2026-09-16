# FIELD//OS Offline Knowledge Sources

AI/ASSIST is deferred. The V3 priority is a useful, maintainable offline library.

FIELD//OS already includes small operator-authored knowledge articles in `config/knowledge/core.yaml`. Those cover fast local workflows such as network triage, Windows IR, evidence integrity, Meshtastic, GNSS, serial, RTL-SDR and hashing. They are deliberately concise and should remain the fast-reference layer.

The external sources below form the deeper reference layer. They should be stored locally on RVN-01 and exposed through LIBRARY without copying large third-party collections into the Project RAV3N Git repository.

## Recommended category tree

```text
~/knowledge/
├── raven/
├── communications/
├── navigation/
├── radio/
├── cybersecurity/
├── computing/
├── emergency/
├── medical/
├── repair/
├── survival/
├── travel/
└── general/
```

## Tier 1 // install first

### Kiwix core library
Use Kiwix for large collections rather than indexing every article into FIELD//OS memory. Recommended initial ZIMs:

- English Wikipedia — broad offline reference
- Wikivoyage — travel, geography and destination reference
- Wiktionary — language/spelling reference
- selected education/repair collections from the Kiwix catalogue

Keep ZIM files on local storage and let Kiwix serve/search them independently. FIELD//OS LIBRARY can later add a launcher/search bridge.

### Raspberry Pi documentation
Official source repository:

`https://github.com/raspberrypi/documentation`

Useful for RVN-01 hardware, Raspberry Pi OS, boot, networking, remote access and configuration troubleshooting. The documentation source is CC BY-SA 4.0.

### Meshtastic documentation
Official documentation repository:

`https://github.com/meshtastic/meshtastic`

Index the documentation subtree locally. This is high-value for device flashing, configuration, regional settings, channels, Bluetooth/serial and mesh operation. Keep the official firmware repository separately if deeper hardware/firmware troubleshooting is required.

### gpsd documentation
Official site:

`https://gpsd.io/`

Retain gpsd/gpspipe/cgps/gpsctl reference material offline. Installing distribution-provided documentation/manpages is preferable where available.

### Australian radio references
Keep local copies of:

- ACMA Australian Radiofrequency Spectrum Plan
- current WIA Australian Amateur Radio Band Plan and posters

These are operational references, not timeless documentation. Store the revision/date next to each local copy and periodically refresh them.

### Cybersecurity reference pack
Keep local copies of:

- MITRE ATT&CK STIX 2.1 dataset
- NIST Cybersecurity Framework 2.0
- NIST SP 800-61r3 Incident Response Recommendations and Considerations

The bundled FIELD//OS articles remain the quick operator layer; these provide authoritative depth.

## Tier 2 // useful additions

### GNU Coreutils manual
A compact local Linux reference. GNU publishes downloadable HTML, plain-text and PDF forms.

### Australian Red Cross RediPlan
Useful offline preparedness guide and emergency-kit checklist. Keep a local personal copy.

### St John Ambulance Australia First Aid Facts
Useful medical quick-reference material, but licensing matters: St John states these fact sheets are for personal use and restricts reproduction/distribution. Do **not** copy them into the public RAV3N repository or redistribute them as part of an image. The operator may keep authorised personal copies on RVN-01 and should refresh them periodically.

## Source-management rules

1. Prefer official sources over mirrors.
2. Record the source URL, local acquisition date and document/version date.
3. Do not silently redistribute third-party copyrighted content through the RAV3N Git repository.
4. Large ZIM/map/document collections live in data storage, not in Git.
5. Regulatory, medical and emergency references need visible revision dates.
6. FIELD//OS-authored quick references should link to or name the deeper source they summarise.
7. Do not require Internet access at FIELD//OS startup; updates are explicit maintenance actions.

The machine-readable catalogue is `config/knowledge/sources.yaml`.
