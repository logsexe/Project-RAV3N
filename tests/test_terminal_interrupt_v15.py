from __future__ import annotations

import unittest
from unittest.mock import Mock

from fieldos.app_v15_recovery import FieldOSApp
from fieldos.hardware.mock import MockTelemetryProvider


class FieldOSV15TerminalInterruptTests(unittest.IsolatedAsyncioTestCase):
    async def test_interrupt_binding_is_priority(self) -> None:
        binding = next(binding for binding in FieldOSApp.BINDINGS if binding.key == "ctrl+c")
        self.assertTrue(binding.priority)

    async def test_interrupt_sends_sigint_to_running_process(self) -> None:
        app = FieldOSApp()
        app.telemetry_provider = MockTelemetryProvider()
        async with app.run_test(size=(100, 30)) as pilot:
            app.render_terminal()
            await pilot.pause()
            session = app.terminals.active
            process = Mock()
            process.returncode = None
            app.running_processes[session.id] = process

            app.action_interrupt()
            await pilot.pause()

            process.send_signal.assert_called_once()
            self.assertIn("INTERRUPT // SIGINT SENT", session.output)


if __name__ == "__main__":
    unittest.main()
