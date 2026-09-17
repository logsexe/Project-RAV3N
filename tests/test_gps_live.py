from __future__ import annotations

import socket
import unittest
from unittest.mock import patch

from fieldos.gps_live import gpsd_snapshot


class _FakeSocket:
    def __init__(self, chunks: list[bytes]):
        self.chunks = list(chunks)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def settimeout(self, timeout: float) -> None:
        pass

    def sendall(self, data: bytes) -> None:
        pass

    def recv(self, size: int) -> bytes:
        if self.chunks:
            return self.chunks.pop(0)
        return b""


class GPSLiveTests(unittest.TestCase):
    def test_collects_device_sky_and_3d_fix(self) -> None:
        payload = (
            b'{"class":"DEVICES","devices":[{"path":"/dev/ttyACM0","driver":"u-blox","subtype":"u-blox 7"}]}\n'
            b'{"class":"SKY","nSat":9,"uSat":6}\n'
            b'{"class":"TPV","mode":3,"lat":-37.8136,"lon":144.9631,"altHAE":42.1,"speed":1.5,"track":270.0}\n'
        )
        with patch("fieldos.gps_live.socket.create_connection", return_value=_FakeSocket([payload])):
            snapshot = gpsd_snapshot(sample_window=0.05)

        self.assertEqual(snapshot.state, "FIX")
        self.assertEqual(snapshot.fix_label, "3D FIX")
        self.assertEqual(snapshot.device, "/dev/ttyACM0")
        self.assertEqual(snapshot.driver, "u-blox")
        self.assertEqual(snapshot.satellites, 9)
        self.assertEqual(snapshot.satellites_used, 6)
        self.assertAlmostEqual(snapshot.latitude or 0.0, -37.8136)
        self.assertAlmostEqual(snapshot.longitude or 0.0, 144.9631)

    def test_reports_satellites_while_waiting_for_fix(self) -> None:
        payload = (
            b'{"class":"DEVICES","devices":[{"path":"/dev/ttyACM0","driver":"u-blox"}]}\n'
            b'{"class":"TPV","mode":1}\n'
            b'{"class":"SKY","nSat":2,"uSat":0}\n'
        )
        with patch("fieldos.gps_live.socket.create_connection", return_value=_FakeSocket([payload])):
            snapshot = gpsd_snapshot(sample_window=0.05)

        self.assertEqual(snapshot.state, "NO FIX")
        self.assertEqual(snapshot.mode, 1)
        self.assertEqual(snapshot.satellites, 2)
        self.assertEqual(snapshot.satellites_used, 0)

    def test_reports_gpsd_offline(self) -> None:
        with patch("fieldos.gps_live.socket.create_connection", side_effect=OSError("offline")):
            snapshot = gpsd_snapshot(sample_window=0.05)
        self.assertEqual(snapshot.state, "GPSD OFFLINE")


if __name__ == "__main__":
    unittest.main()
