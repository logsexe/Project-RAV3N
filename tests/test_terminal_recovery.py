from __future__ import annotations

import unittest

from fieldos.app_v15_recovery import FieldOSApp
from fieldos.hardware.mock import MockTelemetryProvider


class TerminalRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_ctrl_l_action_clears_active_terminal_buffer(self) -> None:
        app = FieldOSApp()
        app.telemetry_provider = MockTelemetryProvider()
        async with app.run_test(size=(100, 30)) as pilot:
            app.render_terminal()
            session = app.terminals.active
            session.append("example output")
            app.action_terminal_clear()
            await pilot.pause()
            self.assertEqual(app.view, "terminal")
            self.assertEqual(session.output, ["TERMINAL // BUFFER CLEARED"])

    async def test_reset_recovers_busy_session(self) -> None:
        app = FieldOSApp()
        app.telemetry_provider = MockTelemetryProvider()
        async with app.run_test(size=(100, 30)) as pilot:
            app.render_terminal()
            session = app.terminals.active
            session.running = True
            session.append("stuck output")
            app.action_terminal_reset()
            await pilot.pause()
            self.assertFalse(session.running)
            self.assertEqual(session.output, ["TERMINAL // SESSION RESET"])


if __name__ == "__main__":
    unittest.main()
