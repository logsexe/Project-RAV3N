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


class GPSDetectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = SystemTelemetryProvider()

    def test_3d_tpv_fix_is_ready(self) -> None:
        payload = '{"class":"VERSION"}\n{"class":"TPV","mode":3,"lat":-27.4,"lon":153.0}'
        with patch("fieldos.hardware.system.shutil.which", side_effect=lambda name: "/usr/bin/gpspipe" if name == "gpspipe" else None), patch(
            "fieldos.hardware.system._run_text", return_value=payload
        ):
            self.assertEqual(self.provider._gps_status(), "READY")

    def test_tpv_without_fix_is_no_fix(self) -> None:
        payload = '{"class":"TPV","mode":1}'
        with patch("fieldos.hardware.system.shutil.which", side_effect=lambda name: "/usr/bin/gpspipe" if name == "gpspipe" else None), patch(
            "fieldos.hardware.system._run_text", return_value=payload
        ):
            self.assertEqual(self.provider._gps_status(), "NO FIX")

    def test_active_gpsd_without_position_is_no_fix(self) -> None:
        def which(name: str):
            return "/usr/bin/systemctl" if name == "systemctl" else None

        with patch("fieldos.hardware.system.shutil.which", side_effect=which), patch(
            "fieldos.hardware.system._run_text", return_value="active"
        ):
            self.assertEqual(self.provider._gps_status(), "NO FIX")

    def test_absent_gps_stack_is_not_present(self) -> None:
        with patch("fieldos.hardware.system.shutil.which", return_value=None):
            self.assertEqual(self.provider._gps_status(), "NOT PRESENT")


class NetworkDetectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = SystemTelemetryProvider()

    def test_global_address_marks_interface_ready(self) -> None:
        payload = '[{"ifname":"wlan0","addr_info":[{"family":"inet","local":"192.168.1.50","scope":"global"}]}]'
        with patch("fieldos.hardware.system.shutil.which", side_effect=lambda name: "/usr/sbin/ip" if name == "ip" else None), patch(
            "fieldos.hardware.system._run_text", return_value=payload
        ):
            self.assertEqual(self.provider._network_status(), "WLAN0")

    def test_up_interface_without_address_is_not_ready(self) -> None:
        payload = '[{"ifname":"wlan0","addr_info":[]}]'
        with patch("fieldos.hardware.system.shutil.which", side_effect=lambda name: "/usr/sbin/ip" if name == "ip" else None), patch(
            "fieldos.hardware.system._run_text", return_value=payload
        ):
            self.assertEqual(self.provider._network_status(), "NO ADDRESS")

    def test_link_local_only_is_reported_separately(self) -> None:
        payload = '[{"ifname":"eth0","addr_info":[{"family":"inet6","local":"fe80::1234","scope":"link"}]}]'
        with patch("fieldos.hardware.system.shutil.which", side_effect=lambda name: "/usr/sbin/ip" if name == "ip" else None), patch(
            "fieldos.hardware.system._run_text", return_value=payload
        ):
            self.assertEqual(self.provider._network_status(), "LINK LOCAL")


if __name__ == "__main__":
    unittest.main()