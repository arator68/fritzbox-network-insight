"""Tests for source-aware WLAN status attributes."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "fritzbox_network_insight"
PACKAGE = "wlan_attribute_test_package"
if PACKAGE not in sys.modules:
    pkg = types.ModuleType(PACKAGE)
    pkg.__path__ = [str(ROOT)]
    sys.modules[PACKAGE] = pkg


def load(name):
    spec = importlib.util.spec_from_file_location(f"{PACKAGE}.{name}", ROOT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


load("device")
model = load("device_details")
formatter = load("wlan_device_attributes")


class WlanDeviceAttributeTests(unittest.TestCase):
    def test_wlan_sources_conflicting_channels_and_zero_rate(self):
        details = model.build_device_details("00:4B:12:69:4D:2C", {})
        details.add("mesh_wifi_channel", 1, source="avm_mesh_radio", observed_at="mesh-time")
        details.add("wifi_channel", 11, source="tr064_wlan_configuration_1", observed_at="tr-time")
        details.add("wifi_rate_rx_mbps", 0, source="avm_mesh_radio", observed_at="mesh-time")
        details.add("wifi_mesh_signal_rx_raw", -31, source="avm_mesh_radio")
        details.add("mesh_reported_link", {"peer_mac": "E0:28:6D:C0:51:38", "link_type": "WLAN"}, source="avm_mesh")
        result = formatter.wlan_details_attribute(details, "802.11")
        by_field = {row["field"]: row for row in result}
        self.assertEqual(by_field["mesh_wifi_channel"]["value"], 1)
        self.assertEqual(by_field["wifi_channel"]["value"], 11)
        self.assertEqual(by_field["wifi_channel"]["observed_at"], "tr-time")
        self.assertEqual(by_field["wifi_rate_rx_mbps"]["value"], 0)
        self.assertEqual(by_field["wifi_mesh_signal_rx_raw"]["value"], -31)
        self.assertNotIn("wifi_signal_rx_dbm", by_field)
        self.assertEqual(by_field["mesh_reported_wlan_peer_mac"]["value"], "E0:28:6D:C0:51:38")

    def test_repeater_diagnostics_are_separate_from_mesh_rates(self):
        details = model.build_device_details("68:F6:3B:6B:48:0A", {})
        details.add("wifi_rate_rx_mbps", 0, source="avm_mesh_radio")
        # Actual repeater response: list Speed=433, specific association Speed=6.
        # Neither is labelled RX, and Mesh RX=0 must remain unchanged.
        details.add("repeater_tr064_wifi_speed_mbps", 433,
                    source="tr064_repeater_diagnostics", observed_at="repeater-time")
        details.add("repeater_tr064_associated_speed_mbps", 6,
                    source="tr064_repeater_diagnostics", observed_at="repeater-time")
        rows = formatter.wlan_details_attribute(details, "802.11")
        by_field = {row["field"]: row for row in rows}
        self.assertEqual(by_field["wifi_rate_rx_mbps"]["value"], 0)
        self.assertEqual(by_field["repeater_tr064_wifi_speed_mbps"]["value"], 433)
        self.assertEqual(by_field["repeater_tr064_associated_speed_mbps"]["value"], 6)
        self.assertEqual(by_field["repeater_tr064_wifi_speed_mbps"]["source"], "tr064_repeater_diagnostics")
        self.assertNotIn("repeater_tr064_wifi_speed_rx_mbps", by_field)

    def test_raw_mesh_rates_preserve_zero_and_units(self):
        details = model.build_device_details("68:F6:3B:6B:48:0A", {})
        details.add("mesh_rate_rx_kbps", 0, source="avm_mesh_radio", observed_at="mesh-time")
        details.add("mesh_rate_tx_kbps", 433000, source="avm_mesh_radio", observed_at="mesh-time")
        rows = formatter.wlan_details_attribute(details, "802.11")
        by_field = {row["field"]: row for row in rows}
        self.assertEqual(by_field["mesh_rate_rx_kbps"]["value"], 0)
        self.assertEqual(by_field["mesh_rate_tx_kbps"]["value"], 433000)
        self.assertEqual(by_field["mesh_rate_rx_kbps"]["source"], "avm_mesh_radio")
        self.assertEqual(by_field["mesh_rate_tx_kbps"]["observed_at"], "mesh-time")

    def test_explicit_mesh_radio_metadata_keeps_source_and_scope(self):
        details = model.build_device_details("00:4B:12:69:4D:2C", {})
        details.add("mesh_wlan_link_radio_fields", {
            "wifi_standard": "n", "stream_count": 1,
            "max_data_rate_rx": 150000, "password": "never expose",
        }, source="avm_mesh_radio", observed_at="mesh-time")
        details.add("mesh_wlan_channel_radio_fields", {
            "channel_width": "20 MHz", "frequency_band": "2.4 GHz",
        }, source="avm_mesh_radio", observed_at="mesh-time")
        rows = formatter.wlan_details_attribute(details, "802.11")
        by_field = {row["field"]: row for row in rows}
        for field in ("wifi_standard", "stream_count", "mesh_radio_channel_width", "frequency_band"):
            self.assertEqual(by_field[field]["source"], "avm_mesh_radio")
            self.assertEqual(by_field[field]["observed_at"], "mesh-time")
        self.assertEqual(by_field["stream_count"]["value"], 1)
        self.assertEqual(by_field["mesh_radio_channel_width"]["value"], "20 MHz")
        self.assertEqual(by_field["mesh_radio_channel_width"]["raw_scope"], "channel")
        self.assertNotIn("password", str(rows))
        self.assertNotIn("max_data_rate_rx", by_field)

    def test_mesh_and_tr064_channel_widths_remain_distinct(self):
        details = model.build_device_details("0C:EF:15:9B:EC:D0", {})
        details.add("wifi_channel_width", 80, source="tr064_wlan_configuration_1", observed_at="tr-time")
        details.add("mesh_wifi_channel_width_raw", "160 MHz", source="avm_mesh_radio", observed_at="mesh-time")
        details.add("mesh_wlan_channel_radio_fields", {"channel_width": "160 MHz"}, source="avm_mesh_radio", observed_at="mesh-time")
        rows = formatter.wlan_details_attribute(details, "802.11")
        by_field = {row["field"]: row for row in rows}
        self.assertEqual(by_field["wifi_channel_width"]["value"], 80)
        self.assertEqual(by_field["wifi_channel_width"]["measurement_scope"], "tr064_wlan_device")
        self.assertEqual(by_field["mesh_radio_channel_width"]["value"], "160 MHz")
        self.assertEqual(by_field["mesh_radio_channel_width"]["measurement_scope"], "mesh_radio_channel")
        self.assertEqual(by_field["mesh_wifi_channel_width_raw"]["measurement_scope"], "mesh_radio_channel")
        self.assertEqual(by_field["mesh_radio_channel_width"]["observed_at"], "mesh-time")
        self.assertEqual(by_field["wifi_channel_width"]["observed_at"], "tr-time")
        self.assertNotIn("channel_width", by_field)

    def test_missing_radio_metadata_is_not_guessed_from_channel(self):
        details = model.build_device_details("00:4B:12:69:4D:2C", {})
        details.add("mesh_wifi_channel", 1, source="avm_mesh_radio")
        rows = formatter.wlan_details_attribute(details, "802.11")
        self.assertEqual([row["field"] for row in rows], ["mesh_wifi_channel"])

    def test_lan_and_unknown_do_not_expose_wlan(self):
        details = model.build_device_details("00:4B:12:69:4D:2C", {})
        details.add("wifi_rate_tx_mbps", 71, source="avm_mesh_radio")
        for interface in ("Ethernet", None, "unknown"):
            self.assertEqual(formatter.wlan_details_attribute(details, interface), [])

    def test_missing_values_are_not_invented(self):
        details = model.build_device_details("00:4B:12:69:4D:2C", {})
        self.assertEqual(formatter.wlan_details_attribute(details, "802.11"), [])
        self.assertEqual(formatter.wlan_details_attribute(None, "802.11"), [])


if __name__ == "__main__":
    unittest.main()
