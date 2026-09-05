from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from fieldos.auth import OperatorAuth
from fieldos.engine import OperationsEngine
from fieldos.maps import OfflineMapStore
from fieldos.profiles import ProfileManager
from fieldos.vault import Vault


class IntelligenceTests(unittest.TestCase):
    def test_assets_evidence_and_timeline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            engine = OperationsEngine(root)
            asset = engine.upsert_asset("FIELD-001", "HOST", "10.0.0.10", label="SERVER")
            source = root / "sample.txt"
            source.write_text("evidence", encoding="utf-8")
            item = engine.ingest_evidence("FIELD-001", source, asset_id=asset.id)
            self.assertTrue(engine.verify_evidence(item.id))
            self.assertEqual(len(engine.list_assets("FIELD-001")), 1)
            self.assertEqual(len(engine.list_evidence("FIELD-001")), 1)
            self.assertGreaterEqual(len(engine.timeline("FIELD-001")), 2)

    def test_encrypted_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            engine = OperationsEngine(root)
            source = root / "sample.bin"
            source.write_bytes(b"secret-data")
            vault = Vault(b"A" * 32)
            item = engine.ingest_evidence("FIELD-001", source, vault=vault)
            self.assertTrue(item.encrypted)
            self.assertTrue(engine.verify_evidence(item.id, vault=vault))
            self.assertNotIn(b"secret-data", Path(item.stored_path).read_bytes())

    def test_profile_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "profile.json"
            manager = ProfileManager(path)
            manager.set("AIRGAP")
            self.assertEqual(ProfileManager(path).current.name, "AIRGAP")

    def test_auth_pin_and_vault_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            auth = OperatorAuth(Path(tmp) / "auth.json")
            auth.configure_pin("123456")
            self.assertFalse(auth.verify_pin("654321"))
            self.assertTrue(auth.verify_pin("123456"))
            self.assertEqual(len(auth.vault_key_from_pin("123456")), 32)

    def test_waypoints(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = OfflineMapStore(Path(tmp) / "maps")
            item = store.add_waypoint(-37.8136, 144.9631, "MELBOURNE", "FIELD-001")
            self.assertEqual(item.id, "WP-0001")
            self.assertEqual(len(store.waypoints()), 1)


if __name__ == "__main__":
    unittest.main()
