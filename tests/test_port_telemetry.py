"""Pure tests for IF-MIB telemetry, independent of Home Assistant."""
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / "custom_components/fritzbox_network_insight/discovery/port_telemetry.py"
spec = importlib.util.spec_from_file_location("port_telemetry_under_test", PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PortTelemetryTests(unittest.TestCase):
    def test_standard_if_mib_values(self):
        rows = module.parse_port_telemetry(
            [("1", "gigabitEthernet 1/0/1"), ("2", "gigabitEthernet 1/0/2")],
            [("1", "1000"), ("2", "0")],
            [("1", "1000000000"), ("2", "100000000")],
            [("1", "1"), ("2", "2")],
        )
        self.assertEqual(rows[0]["reported_speed_mbps"], 1000)
        self.assertEqual(rows[0]["speed_source"], "ifHighSpeed")
        self.assertEqual(rows[0]["oper_status"], "up")
        self.assertEqual(rows[1]["reported_speed_mbps"], 100)
        self.assertEqual(rows[1]["oper_status"], "down")
        self.assertNotIn("duplex", rows[0])
        self.assertNotIn("connected_device", rows[0])

    def test_missing_data_does_not_create_measurements(self):
        rows = module.parse_port_telemetry(
            [("10", "port10")], [], [], []
        )
        self.assertEqual(rows, [{"if_index": 10, "interface_name": "port10"}])

    def test_invalid_and_sentinel_speeds_are_ignored(self):
        rows = module.parse_port_telemetry(
            [("1", "port1")], [("1", "bad")],
            [("1", "4294967295")], [("1", "invalid")],
        )
        self.assertNotIn("reported_speed_mbps", rows[0])
        self.assertNotIn("oper_status", rows[0])


if __name__ == "__main__":
    unittest.main()
