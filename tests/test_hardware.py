from __future__ import annotations

import os
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from fieldos.hardware.system import SystemTelemetryProvider


class MeshDetectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = SystemTelemetryProvider()

    def test_meshtastic_cli_is_ready(self) -> None:
        with patch("fieldos.hardware.system.shutil.which", return_value="/usr/bin/meshtastic"):
            self.assertEqual(self.provider._mesh_status(), "CLI READY")

    def test_no_cli_and_no_explicit_device_is_not_present(self) -> None:
        with patch("fieldos.hardware.system.shutil.which", return_value=None), patch.dict(
            os.environ, {self.provider.MESH_DEVICE_ENV: ""}, clear=False
        ):
            self.assertEqual(self.provider._mesh_status(), "NOT PRESENT")

    def test_explicit_existing_device_is_configured(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            device = Path(tmp) / "mesh-device"
            device.touch()
            with patch("fieldos.hardware.system.shutil.which", return_value=None), patch.dict(
                os.environ, {self.provider.MESH_DEVICE_ENV: str(device)}, clear=False
            ):
                self.assertEqual(self.provider._mesh_status(), "CONFIGURED")

    def test_explicit_missing_device_is_not_present(self) -> None:
        with patch("fieldos.hardware.system.shutil.which", return_value=None), patch.dict(
            os.environ, {self.provider.MESH_DEVICE_ENV: "/definitely/missing/mesh-device"}, clear=False
        ):
            self.assertEqual(self.provider._mesh_status(), "NOT PRESENT")


if __name__ == "__main__":
    unittest.main()
