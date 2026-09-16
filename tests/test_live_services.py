from __future__ import annotations

import subprocess
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

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


class _FakeNlMsg(dict):
    """Stand-in for a pyroute2 netlink message.

    Real pyroute2 messages are dict-like over their fixed struct fields
    (e.g. ``msg["index"]``, ``msg["scope"]``) plus a ``get_attr(name)``
    lookup over their NLA attribute list (e.g. ``msg.get_attr("IFLA_IFNAME")``).
    Field/attribute names below were checked against pyroute2's actual
    ifinfmsg/ifaddrmsg/ndmsg source (fields tuples and nla_map) rather than
    guessed, since pyroute2 itself cannot be installed on this Windows dev
    machine (it's Linux-only) to inspect directly.
    """

    def __init__(self, fields: dict, attrs: dict | None = None) -> None:
        super().__init__(fields)
        self._attrs = attrs or {}

    def get_attr(self, name: str):
        return self._attrs.get(name)


def _fake_pyroute2_module(ipr: MagicMock) -> types.ModuleType:
    module = types.ModuleType("pyroute2")
    module.IPRoute = MagicMock(return_value=ipr)  # type: ignore[attr-defined]
    return module


def _fake_ipr(**method_returns) -> MagicMock:
    ipr = MagicMock()
    for name, value in method_returns.items():
        getattr(ipr, name).return_value = value
    ipr.__enter__ = MagicMock(return_value=ipr)
    ipr.__exit__ = MagicMock(return_value=False)
    return ipr


class NetworkInterfacesTests(unittest.TestCase):
    def setUp(self) -> None:
        # These tests exercise the `ip`-subprocess fallback specifically.
        # pyroute2 is now a real, functional core dependency on Linux (see
        # pyproject.toml's `sys_platform == "linux"` marker), which is
        # exactly the platform CI runs on - so without pinning sys.platform
        # away from "linux" here, these tests would stop using the mocked
        # `_run` output on CI once pyroute2 installs there, and would instead
        # silently read the CI runner's own real interface/neighbour tables.
        # Forcing pyroute2 off (rather than uninstalling it) is what makes
        # this a fallback test regardless of what happens to be installed.
        patcher = patch("fieldos.live_services.sys.platform", "win32")
        patcher.start()
        self.addCleanup(patcher.stop)

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
    def setUp(self) -> None:
        # See NetworkInterfacesTests.setUp: pins pyroute2 off so these tests
        # deterministically exercise the `ip`-subprocess fallback regardless
        # of whether pyroute2 is actually installed in this environment.
        patcher = patch("fieldos.live_services.sys.platform", "win32")
        patcher.start()
        self.addCleanup(patcher.stop)

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


class NetworkInterfacesPyroute2Tests(unittest.TestCase):
    """The netlink path, mocked - pyroute2 itself can't be installed or
    exercised for real on this Windows dev machine (it's Linux-only). These
    tests validate the parsing/classification logic against message shapes
    checked against pyroute2's actual source; the real netlink calls
    themselves are only exercised for real on CI (ubuntu-latest)."""

    def test_global_address_is_reported(self) -> None:
        link = _FakeNlMsg({"index": 3, "flags": 0x1}, {"IFLA_IFNAME": "wlan0"})
        addr = _FakeNlMsg({"index": 3, "scope": 0}, {"IFA_LOCAL": "192.168.1.50"})
        ipr = _fake_ipr(get_links=[link], get_addr=[addr])
        with patch("fieldos.live_services.sys.platform", "linux"), patch(
            "fieldos.live_services.importlib.util.find_spec",
            side_effect=lambda name: object() if name == "pyroute2" else None,
        ), patch.dict(sys.modules, {"pyroute2": _fake_pyroute2_module(ipr)}):
            result = network_interfaces()
        self.assertEqual(result, (NetworkInterface("WLAN0", "GLOBAL", "192.168.1.50"),))

    def test_loopback_is_excluded(self) -> None:
        link = _FakeNlMsg({"index": 1, "flags": 0x1}, {"IFLA_IFNAME": "lo"})
        addr = _FakeNlMsg({"index": 1, "scope": 254}, {"IFA_LOCAL": "127.0.0.1"})
        ipr = _fake_ipr(get_links=[link], get_addr=[addr])
        with patch("fieldos.live_services.sys.platform", "linux"), patch(
            "fieldos.live_services.importlib.util.find_spec",
            side_effect=lambda name: object() if name == "pyroute2" else None,
        ), patch.dict(sys.modules, {"pyroute2": _fake_pyroute2_module(ipr)}):
            self.assertEqual(network_interfaces(), ())

    def test_down_interface_is_excluded(self) -> None:
        link = _FakeNlMsg({"index": 4, "flags": 0x0}, {"IFLA_IFNAME": "eth1"})
        ipr = _fake_ipr(get_links=[link], get_addr=[])
        with patch("fieldos.live_services.sys.platform", "linux"), patch(
            "fieldos.live_services.importlib.util.find_spec",
            side_effect=lambda name: object() if name == "pyroute2" else None,
        ), patch.dict(sys.modules, {"pyroute2": _fake_pyroute2_module(ipr)}):
            self.assertEqual(network_interfaces(), ())

    def test_link_local_only_is_reported_separately(self) -> None:
        link = _FakeNlMsg({"index": 5, "flags": 0x1}, {"IFLA_IFNAME": "eth0"})
        addr = _FakeNlMsg({"index": 5, "scope": 253}, {"IFA_LOCAL": "fe80::1234"})
        ipr = _fake_ipr(get_links=[link], get_addr=[addr])
        with patch("fieldos.live_services.sys.platform", "linux"), patch(
            "fieldos.live_services.importlib.util.find_spec",
            side_effect=lambda name: object() if name == "pyroute2" else None,
        ), patch.dict(sys.modules, {"pyroute2": _fake_pyroute2_module(ipr)}):
            result = network_interfaces()
        self.assertEqual(result, (NetworkInterface("ETH0", "LINK LOCAL", "fe80::1234"),))

    def test_pyroute2_unavailable_falls_back_to_ip_subprocess(self) -> None:
        payload = '[{"ifname":"wlan0","addr_info":[{"family":"inet","local":"192.168.1.50","scope":"global"}]}]'
        with patch("fieldos.live_services.sys.platform", "linux"), patch(
            "fieldos.live_services.importlib.util.find_spec", return_value=None
        ), patch(
            "fieldos.live_services.shutil.which", side_effect=lambda name: "/usr/sbin/ip" if name == "ip" else None
        ), patch("fieldos.live_services._run", return_value=_completed(payload)):
            result = network_interfaces()
        self.assertEqual(result, (NetworkInterface("WLAN0", "GLOBAL", "192.168.1.50"),))

    def test_pyroute2_runtime_failure_falls_back_to_ip_subprocess(self) -> None:
        payload = '[{"ifname":"wlan0","addr_info":[{"family":"inet","local":"192.168.1.50","scope":"global"}]}]'
        broken_module = types.ModuleType("pyroute2")
        broken_module.IPRoute = MagicMock(side_effect=RuntimeError("netlink socket refused"))  # type: ignore[attr-defined]
        with patch("fieldos.live_services.sys.platform", "linux"), patch(
            "fieldos.live_services.importlib.util.find_spec",
            side_effect=lambda name: object() if name == "pyroute2" else None,
        ), patch.dict(sys.modules, {"pyroute2": broken_module}), patch(
            "fieldos.live_services.shutil.which", side_effect=lambda name: "/usr/sbin/ip" if name == "ip" else None
        ), patch("fieldos.live_services._run", return_value=_completed(payload)):
            result = network_interfaces()
        self.assertEqual(result, (NetworkInterface("WLAN0", "GLOBAL", "192.168.1.50"),))


class NetworkNeighboursPyroute2Tests(unittest.TestCase):
    """The netlink path, mocked - see NetworkInterfacesPyroute2Tests for why."""

    def test_neighbours_are_parsed(self) -> None:
        link = _FakeNlMsg({"index": 3}, {"IFLA_IFNAME": "wlan0"})
        neighbour = _FakeNlMsg({"ifindex": 3, "state": 0x02}, {"NDA_DST": "192.168.1.1", "NDA_LLADDR": "aa:bb:cc:dd:ee:ff"})
        ipr = _fake_ipr(get_neighbours=[neighbour], get_links=[link])
        with patch("fieldos.live_services.sys.platform", "linux"), patch(
            "fieldos.live_services.importlib.util.find_spec",
            side_effect=lambda name: object() if name == "pyroute2" else None,
        ), patch.dict(sys.modules, {"pyroute2": _fake_pyroute2_module(ipr)}):
            result = network_neighbours()
        self.assertEqual(result, (NetworkNeighbour("192.168.1.1", "wlan0", "aa:bb:cc:dd:ee:ff", "REACHABLE"),))

    def test_empty_destination_is_excluded(self) -> None:
        link = _FakeNlMsg({"index": 3}, {"IFLA_IFNAME": "wlan0"})
        neighbour = _FakeNlMsg({"ifindex": 3, "state": 0x40}, {})
        ipr = _fake_ipr(get_neighbours=[neighbour], get_links=[link])
        with patch("fieldos.live_services.sys.platform", "linux"), patch(
            "fieldos.live_services.importlib.util.find_spec",
            side_effect=lambda name: object() if name == "pyroute2" else None,
        ), patch.dict(sys.modules, {"pyroute2": _fake_pyroute2_module(ipr)}):
            self.assertEqual(network_neighbours(), ())

    def test_respects_limit(self) -> None:
        link = _FakeNlMsg({"index": 1}, {"IFLA_IFNAME": "eth0"})
        neighbours = [
            _FakeNlMsg({"ifindex": 1, "state": 0x04}, {"NDA_DST": f"10.0.0.{i}"}) for i in range(5)
        ]
        ipr = _fake_ipr(get_neighbours=neighbours, get_links=[link])
        with patch("fieldos.live_services.sys.platform", "linux"), patch(
            "fieldos.live_services.importlib.util.find_spec",
            side_effect=lambda name: object() if name == "pyroute2" else None,
        ), patch.dict(sys.modules, {"pyroute2": _fake_pyroute2_module(ipr)}):
            result = network_neighbours(limit=2)
        self.assertEqual(len(result), 2)

    def test_pyroute2_unavailable_falls_back_to_ip_subprocess(self) -> None:
        payload = '[{"dst":"192.168.1.1","dev":"wlan0","lladdr":"aa:bb:cc:dd:ee:ff","state":["REACHABLE"]}]'
        with patch("fieldos.live_services.sys.platform", "linux"), patch(
            "fieldos.live_services.importlib.util.find_spec", return_value=None
        ), patch(
            "fieldos.live_services.shutil.which", side_effect=lambda name: "/usr/sbin/ip" if name == "ip" else None
        ), patch("fieldos.live_services._run", return_value=_completed(payload)):
            result = network_neighbours()
        self.assertEqual(result, (NetworkNeighbour("192.168.1.1", "wlan0", "aa:bb:cc:dd:ee:ff", "REACHABLE"),))

    def test_pyroute2_runtime_failure_falls_back_to_ip_subprocess(self) -> None:
        payload = '[{"dst":"192.168.1.1","dev":"wlan0","lladdr":"aa:bb:cc:dd:ee:ff","state":["REACHABLE"]}]'
        broken_module = types.ModuleType("pyroute2")
        broken_module.IPRoute = MagicMock(side_effect=RuntimeError("netlink socket refused"))  # type: ignore[attr-defined]
        with patch("fieldos.live_services.sys.platform", "linux"), patch(
            "fieldos.live_services.importlib.util.find_spec",
            side_effect=lambda name: object() if name == "pyroute2" else None,
        ), patch.dict(sys.modules, {"pyroute2": broken_module}), patch(
            "fieldos.live_services.shutil.which", side_effect=lambda name: "/usr/sbin/ip" if name == "ip" else None
        ), patch("fieldos.live_services._run", return_value=_completed(payload)):
            result = network_neighbours()
        self.assertEqual(result, (NetworkNeighbour("192.168.1.1", "wlan0", "aa:bb:cc:dd:ee:ff", "REACHABLE"),))


class MeshtasticNodesTests(unittest.TestCase):
    def test_meshtastic_not_installed_fails_closed(self) -> None:
        with patch("fieldos.live_services.importlib.util.find_spec", return_value=None):
            self.assertEqual(meshtastic_nodes(), ())

    def test_serial_interface_unavailable_fails_closed(self) -> None:
        with patch("fieldos.live_services.open_meshtastic_interface", return_value=None):
            self.assertEqual(meshtastic_nodes(), ())

    def test_close_failure_does_not_propagate(self) -> None:
        class BrokenInterface:
            nodes = {"!abc123": {"user": {"longName": "Base Camp"}, "lastHeard": 1234}}

            def close(self) -> None:
                raise AttributeError("stream")

        with patch("fieldos.live_services.open_meshtastic_interface", return_value=BrokenInterface()):
            result = meshtastic_nodes()
        self.assertEqual(result, (MeshNode("!abc123", "Base Camp", "1234"),))


if __name__ == "__main__":
    unittest.main()
