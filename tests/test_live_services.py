from __future__ import annotations

import subprocess
import unittest
from unittest.mock import patch

from fieldos.live_services import (
    MeshNode,
    NetworkInterface,
    NetworkNeighbour,
    meshtastic_nodes,
    network_interfaces,
    network_neighbours,
)


def _completed(stdout: str, returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")


class NetworkInterfacesTests(unittest.TestCase):
    def test_global_address_is_reported(self) -> None:
        payload = '[{"ifname":"wlan0","addr_info":[{"family":"inet","local":"192.168.1.50","scope":"global"}]}]'
        with patch("fieldos.live_services.shutil.which", side_effect=lambda name: "/usr/sbin/ip" if name == "ip" else None), patch(
            "fieldos.live_services._run", return_value=_completed(payload)
        ):
            result = network_interfaces()
        self.assertEqual(result, (NetworkInterface("WLAN0", "GLOBAL", "192.168.1.50"),))

    def test_loopback_is_excluded(self) -> None:
        payload = '[{"ifname":"lo","addr_info":[{"family":"inet","local":"127.0.0.1","scope":"host"}]}]'
        with patch("fieldos.live_services.shutil.which", side_effect=lambda name: "/usr/sbin/ip" if name == "ip" else None), patch(
            "fieldos.live_services._run", return_value=_completed(payload)
        ):
            self.assertEqual(network_interfaces(), ())

    def test_link_local_only_is_reported_separately(self) -> None:
        payload = '[{"ifname":"eth0","addr_info":[{"family":"inet6","local":"fe80::1234","scope":"link"}]}]'
        with patch("fieldos.live_services.shutil.which", side_effect=lambda name: "/usr/sbin/ip" if name == "ip" else None), patch(
            "fieldos.live_services._run", return_value=_completed(payload)
        ):
            result = network_interfaces()
        self.assertEqual(result, (NetworkInterface("ETH0", "LINK LOCAL", "fe80::1234"),))

    def test_no_ip_binary_falls_back_to_names_only(self) -> None:
        with patch("fieldos.live_services.shutil.which", return_value=None), patch(
            "fieldos.live_services.socket.if_nameindex", return_value=[(1, "lo"), (2, "eth0")]
        ):
            result = network_interfaces()
        self.assertEqual(result, (NetworkInterface("ETH0", "UNKNOWN"),))


class NetworkNeighboursTests(unittest.TestCase):
    def test_neighbours_are_parsed(self) -> None:
        payload = '[{"dst":"192.168.1.1","dev":"wlan0","lladdr":"aa:bb:cc:dd:ee:ff","state":["REACHABLE"]}]'
        with patch("fieldos.live_services.shutil.which", side_effect=lambda name: "/usr/sbin/ip" if name == "ip" else None), patch(
            "fieldos.live_services._run", return_value=_completed(payload)
        ):
            result = network_neighbours()
        self.assertEqual(result, (NetworkNeighbour("192.168.1.1", "wlan0", "aa:bb:cc:dd:ee:ff", "REACHABLE"),))

    def test_no_ip_binary_returns_empty(self) -> None:
        with patch("fieldos.live_services.shutil.which", return_value=None):
            self.assertEqual(network_neighbours(), ())

    def test_respects_limit(self) -> None:
        records = [{"dst": f"10.0.0.{i}", "dev": "eth0", "state": []} for i in range(5)]
        import json

        with patch("fieldos.live_services.shutil.which", side_effect=lambda name: "/usr/sbin/ip" if name == "ip" else None), patch(
            "fieldos.live_services._run", return_value=_completed(json.dumps(records))
        ):
            result = network_neighbours(limit=2)
        self.assertEqual(len(result), 2)


class MeshtasticNodesTests(unittest.TestCase):
    def test_meshtastic_not_installed_fails_closed(self) -> None:
        with patch("fieldos.live_services.importlib.util.find_spec", return_value=None):
            self.assertEqual(meshtastic_nodes(), ())

    def test_serial_interface_unavailable_fails_closed(self) -> None:
        with patch("fieldos.live_services._meshtastic_serial_interface", return_value=None):
            self.assertEqual(meshtastic_nodes(), ())

    def test_close_failure_does_not_propagate(self) -> None:
        class BrokenInterface:
            nodes = {"!abc123": {"user": {"longName": "Base Camp"}, "lastHeard": 1234}}

            def close(self) -> None:
                raise AttributeError("stream")

        with patch("fieldos.live_services._meshtastic_serial_interface", return_value=BrokenInterface()):
            result = meshtastic_nodes()
        self.assertEqual(result, (MeshNode("!abc123", "Base Camp", "1234"),))


if __name__ == "__main__":
    unittest.main()
