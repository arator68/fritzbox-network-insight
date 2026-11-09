"""Regression tests for per-device numeric WLAN sensor values."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "fritzbox_network_insight"
PACKAGE = "wlan_metric_test_package"
pkg = types.ModuleType(PACKAGE)
pkg.__path__ = [str(ROOT)]
sys.modules[PACKAGE] = pkg
spec = importlib.util.spec_from_file_location(f"{PACKAGE}.wlan_metric_sensors", ROOT / "wlan_metric_sensors.py")
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class WlanMetricTests(unittest.TestCase):
    def test_separate_radio_scopes(self):
        rows = [
            {"field": "wifi_channel_width", "value": 80, "source": "tr064", "measurement_scope": "tr064_wlan_device"},
            {"field": "mesh_radio_channel_width", "value": "160 MHz", "source": "avm_mesh", "measurement_scope": "mesh_radio_channel"},
        ]
        self.assertEqual(module.metric_observation(rows, "channel_width")["value"], 80)
        self.assertEqual(module.metric_observation(rows, "mesh_channel_width")["value"], 160)
        self.assertEqual(module.metric_observation(rows, "mesh_channel_width")["source"], "avm_mesh")

    def test_missing_and_invalid_are_unavailable(self):
        self.assertIsNone(module.metric_observation([], "channel_width"))
        self.assertIsNone(module.metric_observation([{"field": "mesh_radio_channel_width", "value": "unknown", "measurement_scope": "mesh_radio_channel"}], "mesh_channel_width"))
        self.assertIsNone(module.metric_observation([{"field": "wifi_channel_width", "value": 160, "measurement_scope": "mesh_radio_channel"}], "channel_width"))

    def test_mesh_channel_and_signals_are_source_specific(self):
        rows = [
            {"field": "mesh_wifi_channel", "value": 104, "source": "avm_mesh"},
            {"field": "mesh_rx_rcpi_raw", "value": -57, "source": "avm_mesh"},
            {"field": "mesh_tx_rcpi_raw", "value": -53, "source": "avm_mesh"},
        ]
        self.assertEqual(module.metric_observation(rows, "mesh_channel")["value"], 104)
        self.assertEqual(module.metric_observation(rows, "mesh_signal_rx_raw")["value"], -57)
        self.assertEqual(module.metric_observation(rows, "mesh_signal_tx_raw")["value"], -53)
        self.assertIsNone(module.metric_observation(rows, "channel"))
        self.assertIsNone(module.metric_observation([{"field": "mesh_rx_rcpi_raw", "value": 255}], "mesh_signal_rx_raw"))

    def test_zero_rate_is_valid(self):
        self.assertEqual(module.metric_observation([{"field": "wifi_rate_rx_mbps", "value": 0}], "rx_rate")["value"], 0)


if __name__ == "__main__":
    unittest.main()
