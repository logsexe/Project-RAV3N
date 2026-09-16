import unittest

from fieldos.hardware.mock import Telemetry
from fieldos.hardware.readiness import SubsystemState, assess_telemetry, classify


class ReadinessModelTests(unittest.TestCase):
    def test_ready_values_are_healthy(self):
        self.assertEqual(classify("network", "WLAN0").state, SubsystemState.READY)
        self.assertEqual(classify("gps", "READY").state, SubsystemState.READY)
        self.assertEqual(classify("mesh", "CLI READY").state, SubsystemState.READY)

    def test_absent_and_unknown_are_not_healthy(self):
        self.assertEqual(classify("gps", "NOT PRESENT").state, SubsystemState.ABSENT)
        self.assertEqual(classify("mesh", "UNKNOWN").state, SubsystemState.UNKNOWN)

    def test_network_no_address_is_degraded(self):
        item = classify("network", "NO ADDRESS")
        self.assertEqual(item.state, SubsystemState.DEGRADED)
        self.assertFalse(item.healthy)

    def test_assessment_collects_advisories(self):
        telemetry = Telemetry(
            mesh="NOT PRESENT",
            gps="NO FIX",
            network="WLAN0",
            cpu_temp_c=80.0,
            storage_percent=20,
            battery_percent=-1,
        )
        assessment = assess_telemetry(telemetry)
        self.assertEqual(assessment.state, "DEGRADED")
        self.assertIn("GPS NO FIX", assessment.advisories)
        self.assertIn("MESH NOT PRESENT", assessment.advisories)
        self.assertIn("CPU HOT 80C", assessment.advisories)

    def test_nominal_assessment_is_ready(self):
        telemetry = Telemetry(
            mesh="CLI READY",
            gps="READY",
            network="WLAN0",
            cpu_temp_c=55.0,
            storage_percent=20,
            battery_percent=-1,
        )
        self.assertEqual(assess_telemetry(telemetry).state, "READY")


if __name__ == "__main__":
    unittest.main()
