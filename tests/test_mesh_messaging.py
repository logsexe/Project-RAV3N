from __future__ import annotations

import os
import tempfile
import time
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from fieldos.qt_field_app import FieldOSWindow


class FakeMeshInterface:
    """Stands in for meshtastic.serial_interface.SerialInterface in tests."""

    def __init__(self, nodes=None):
        self.nodes = nodes or {}
        self.sent: list[str] = []
        self.closed = False

    def sendText(self, text: str) -> None:
        self.sent.append(text)

    def close(self) -> None:
        self.closed = True


class MeshMessagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.qt_app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._prev_data_dir = os.environ.get("FIELDOS_DATA_DIR")
        os.environ["FIELDOS_DATA_DIR"] = self._tmp.name
        self.window = FieldOSWindow()
        self.qt_app.processEvents()
        self.window.open_app("MESH")
        self.qt_app.processEvents()

    def tearDown(self) -> None:
        self.window.close()
        self.qt_app.processEvents()
        if self._prev_data_dir is None:
            os.environ.pop("FIELDOS_DATA_DIR", None)
        else:
            os.environ["FIELDOS_DATA_DIR"] = self._prev_data_dir
        self._tmp.cleanup()

    def _drain(self, *keys: str, timeout: float = 5.0) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline and any(key in self.window.futures for key in keys):
            self.qt_app.processEvents()
            time.sleep(0.02)
        self.qt_app.processEvents()

    def test_starts_disconnected(self) -> None:
        self.assertIsNone(self.window.mesh_interface)
        self.assertEqual(self.window.mesh_connect_button.text(), "CONNECT")

    def test_connect_failure_reports_status_and_stays_disconnected(self) -> None:
        with patch("fieldos.qt_field_app.open_meshtastic_interface", return_value=None):
            self.window._toggle_mesh_connection()
            self._drain("MESHCONNECT")

        self.assertIsNone(self.window.mesh_interface)
        self.assertIn("CONNECT FAILED", self.window.mesh_status.text())
        self.assertTrue(self.window.mesh_connect_button.isEnabled())

    def test_connect_success_switches_to_persistent_mode(self) -> None:
        fake = FakeMeshInterface(nodes={"!aabbccdd": {"user": {"longName": "Base Node"}, "lastHeard": 100}})
        with patch("fieldos.qt_field_app.open_meshtastic_interface", return_value=fake):
            self.window._toggle_mesh_connection()
            self._drain("MESHCONNECT")

        self.assertIs(self.window.mesh_interface, fake)
        self.assertEqual(self.window.mesh_connect_button.text(), "DISCONNECT")
        self.assertIn("CONNECTED (PERSISTENT)", self.window.mesh_status.text())
        self.assertEqual(self.window.mesh_nodes_list.count(), 1)
        self.assertIn("Base Node", self.window.mesh_nodes_list.item(0).text())

    def test_refresh_while_connected_reads_persistent_interface_not_a_new_probe(self) -> None:
        # setUp()'s initial open_app("MESH") already queued a one-shot
        # MESHNODES probe (mesh_interface was still None then) - drain it
        # before checking that a *subsequent* refresh, now connected, takes
        # the persistent-read path instead of queuing another one.
        self._drain("MESHNODES")
        fake = FakeMeshInterface(nodes={"!11": {"user": {"longName": "Node One"}}})
        self.window.mesh_interface = fake
        self.window.refresh_module("MESH")
        self.assertNotIn("MESHNODES", self.window.futures)
        self.assertEqual(self.window.mesh_nodes_list.count(), 1)
        self.assertIn("Node One", self.window.mesh_nodes_list.item(0).text())

    def test_send_without_connection_is_rejected(self) -> None:
        self.window.mesh_message_input.setText("hello")
        self.window._send_mesh_message()
        self.assertIn("NOT CONNECTED", self.window.footer.text())
        self.assertEqual(self.window.mesh_messages_list.count(), 0)

    def test_send_with_connection_calls_sendtext_and_logs_it(self) -> None:
        fake = FakeMeshInterface()
        self.window.mesh_interface = fake
        self.window.mesh_message_input.setText("status green")
        self.window._send_mesh_message()

        self.assertEqual(fake.sent, ["status green"])
        self.assertEqual(self.window.mesh_messages_list.count(), 1)
        self.assertIn("status green", self.window.mesh_messages_list.item(0).text())
        self.assertEqual(self.window.mesh_message_input.text(), "")

        events = self.window.ops_engine.timeline(self.window.operations.active.id)
        self.assertTrue(any(event.event_type == "MESH-TX" for event in events))

    def test_send_failure_reports_error_and_does_not_log_a_sent_message(self) -> None:
        class BrokenSend(FakeMeshInterface):
            def sendText(self, text: str) -> None:
                raise RuntimeError("radio busy")

        self.window.mesh_interface = BrokenSend()
        self.window.mesh_message_input.setText("hello")
        self.window._send_mesh_message()

        self.assertIn("SEND FAILED", self.window.footer.text())
        self.assertEqual(self.window.mesh_messages_list.count(), 0)

    def test_incoming_text_message_via_pubsub_callback_updates_log_and_ops_timeline(self) -> None:
        fake = FakeMeshInterface(nodes={"!aabbccdd": {"user": {"longName": "Base Node"}}})
        self.window.mesh_interface = fake
        packet = {
            "decoded": {"portnum": "TEXT_MESSAGE_APP", "text": "all clear"},
            "fromId": "!aabbccdd",
            "from": "!aabbccdd",
        }

        self.window._mesh_pubsub_callback(packet=packet, interface=fake)
        self.qt_app.processEvents()

        self.assertEqual(self.window.mesh_messages_list.count(), 1)
        text = self.window.mesh_messages_list.item(0).text()
        self.assertIn("Base Node", text)
        self.assertIn("all clear", text)

        events = self.window.ops_engine.timeline(self.window.operations.active.id)
        self.assertTrue(any(event.event_type == "MESH-RX" for event in events))

    def test_non_text_packet_is_ignored(self) -> None:
        fake = FakeMeshInterface()
        self.window.mesh_interface = fake
        packet = {"decoded": {"portnum": "POSITION_APP"}, "fromId": "!11"}

        self.window._mesh_pubsub_callback(packet=packet, interface=fake)
        self.qt_app.processEvents()

        self.assertEqual(self.window.mesh_messages_list.count(), 0)

    def test_disconnect_closes_interface_and_resets_state(self) -> None:
        fake = FakeMeshInterface()
        self.window.mesh_interface = fake
        self.window.mesh_connect_button.setText("DISCONNECT")

        self.window._disconnect_mesh()

        self.assertTrue(fake.closed)
        self.assertIsNone(self.window.mesh_interface)
        self.assertEqual(self.window.mesh_connect_button.text(), "CONNECT")
        self.assertIn("DISCONNECTED", self.window.mesh_status.text())

    def test_toggle_connection_disconnects_when_already_connected(self) -> None:
        fake = FakeMeshInterface()
        self.window.mesh_interface = fake
        self.window._toggle_mesh_connection()
        self.assertTrue(fake.closed)
        self.assertIsNone(self.window.mesh_interface)


if __name__ == "__main__":
    unittest.main()
