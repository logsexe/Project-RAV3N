from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from fieldos.engine import OperationsEngine
from fieldos.integrations import IntegrationHub


class IntegrationTests(unittest.TestCase):
    def test_nmap_xml_creates_asset_and_service_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            engine = OperationsEngine(root / "data")
            sample = root / "scan.xml"
            sample.write_text(
                """<?xml version='1.0'?>
<nmaprun><host><status state='up'/><address addr='192.0.2.10' addrtype='ipv4'/>
<hostnames><hostname name='demo.local'/></hostnames><ports><port protocol='tcp' portid='22'>
<state state='open'/><service name='ssh' product='OpenSSH'/></port></ports></host></nmaprun>""",
                encoding="utf-8",
            )
            result = IntegrationHub(engine).import_file("OP-TEST", "nmap", sample)
            self.assertEqual(result.assets, 1)
            self.assertEqual(result.events, 1)
            assets = engine.list_assets("OP-TEST")
            self.assertEqual(assets[0].value, "192.0.2.10")
            events = engine.timeline("OP-TEST")
            self.assertTrue(any(item.event_type == "SERVICE" for item in events))

    def test_gnss_json_lines_creates_timeline_event(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            engine = OperationsEngine(root / "data")
            sample = root / "gps.jsonl"
            sample.write_text(json.dumps({"class": "TPV", "lat": -27.5, "lon": 153.0, "mode": 3}) + "\n", encoding="utf-8")
            result = IntegrationHub(engine).import_file("OP-TEST", "gnss", sample)
            self.assertEqual(result.events, 1)
            self.assertTrue(any(item.event_type == "GNSS" for item in engine.timeline("OP-TEST")))

    def test_meshtastic_json_creates_node_asset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            engine = OperationsEngine(root / "data")
            sample = root / "mesh.json"
            sample.write_text(json.dumps({"nodes": [{"user": {"id": "!abcd1234", "longName": "RAVEN NODE"}}]}), encoding="utf-8")
            result = IntegrationHub(engine).import_file("OP-TEST", "meshtastic", sample)
            self.assertEqual(result.assets, 1)
            self.assertEqual(engine.list_assets("OP-TEST")[0].kind, "MESH_NODE")

    def test_osint_json_promotes_common_selectors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            engine = OperationsEngine(root / "data")
            sample = root / "intel.json"
            sample.write_text(json.dumps({"results": [{"domain": "example.org", "ip": "192.0.2.20"}]}), encoding="utf-8")
            result = IntegrationHub(engine).import_file("OP-TEST", "osint-json", sample)
            self.assertEqual(result.assets, 2)
            kinds = {item.kind for item in engine.list_assets("OP-TEST")}
            self.assertEqual(kinds, {"DOMAIN", "IP"})


if __name__ == "__main__":
    unittest.main()
