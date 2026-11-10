"""Mesh radio detail extraction is independent of topology construction."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "fritzbox_network_insight"
PACKAGE = "fritzbox_network_insight"
if PACKAGE not in sys.modules:
    package = types.ModuleType(PACKAGE)
    package.__path__ = [str(ROOT)]
    sys.modules[PACKAGE] = package

for name in ("device", "mesh_wlan_details"):
    spec = importlib.util.spec_from_file_location(f"{PACKAGE}.{name}", ROOT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

extract = sys.modules[f"{PACKAGE}.mesh_wlan_details"].extract_mesh_wlan_details


class TestMeshWlanDetails(unittest.TestCase):
    def test_ap_peer_metrics_do_not_mutate_mesh(self):
        import copy
        payload = {"nodes": [
            {"uid": "ap", "mesh_role": "master", "node_interfaces": [{
                "type": "WLAN", "current_channel": 11,
                "current_channel_info": {"channel_width": "20 MHz"},
                "node_links": [{"uid": "link", "state": "CONNECTED",
                    "node_1_uid": "ap", "node_2_uid": "client",
                    "rx_rcpi": -55, "tx_rcpi": -57,
                    "cur_data_rate_rx": 86000, "cur_data_rate_tx": 68000,
                    "max_data_rate_rx": 143400, "max_data_rate_tx": 143400}]
            }]},
            {"uid": "client", "device_mac_address": "20:6E:F1:02:62:D8",
             "node_interfaces": []},
        ]}
        original = copy.deepcopy(payload)
        data = extract(payload, {"20:6E:F1:02:62:D8": "20:6E:F1:02:62:D8"})
        self.assertEqual(payload, original)
        radio = data["20:6E:F1:02:62:D8"][0]
        self.assertEqual(radio["mesh_rx_rcpi_raw"], -55)
        self.assertTrue(radio["mesh_rate_link_owner_is_node_1"])
        self.assertFalse(radio["mesh_rate_client_is_node_1"])
        self.assertFalse(radio["mesh_rate_link_has_source_target"])
        self.assertEqual(radio["mesh_rate_rx_kbps"], 86000)
        self.assertEqual(radio["mesh_wifi_channel"], 11)
        self.assertEqual(radio["wifi_rate_rx_mbps"], 86)
        self.assertEqual(radio["wifi_rate_tx_mbps"], 68)
        self.assertEqual(radio["wifi_rate_rx_max_mbps"], 143.4)
        self.assertEqual(radio["wifi_rate_tx_max_mbps"], 143.4)
        self.assertEqual(radio["wifi_mesh_signal_rx_raw"], -55)
        self.assertNotIn("wifi_signal_dbm", radio)

    def test_radio_schema_fields_only_allow_safe_scalars(self):
        payload = {"nodes": [
            {"uid": "ap", "mesh_role": "master", "node_interfaces": [{
                "type": "WLAN", "current_channel_info": {
                    "channel_width": "20 MHz", "secret": "not shown"
                },
                "node_links": [{
                    "uid": "link", "state": "CONNECTED",
                    "node_1_uid": "ap", "node_2_uid": "client",
                    "max_data_rate_rx": 143000,
                    "wifi_standard": "ax", "password": "hidden",
                    "stream_count": 1, "mimo_detail": {"secret": "hidden"}
                }]
            }]},
            {"uid": "client", "device_mac_address": "20:6E:F1:02:62:D8"},
        ]}
        data = extract(payload, {"20:6E:F1:02:62:D8": "20:6E:F1:02:62:D8"})
        radio = data["20:6E:F1:02:62:D8"][0]
        self.assertEqual(radio["mesh_wlan_link_radio_fields"], {
            "max_data_rate_rx": 143000, "wifi_standard": "ax",
            "stream_count": 1,
        })
        self.assertEqual(radio["mesh_wlan_channel_radio_fields"], {
            "channel_width": "20 MHz",
        })
        self.assertNotIn("password", str(radio))
        self.assertNotIn("secret", str(radio))

    def test_avm_rate_directions_preserved_without_ui_assumptions(self):
        """The parser preserves AVM rx/tx fields; UI arrow semantics are separate."""
        payload = {"nodes": [
            {"uid": "ap", "mesh_role": "slave", "node_interfaces": [{
                "type": "WLAN", "current_channel": 1,
                "current_channel_info": {"channel_width": "20 MHz"},
                "node_links": [{"uid": "link", "state": "CONNECTED",
                    "node_1_uid": "ap", "node_2_uid": "client",
                    "cur_data_rate_rx": 0, "cur_data_rate_tx": 71000,
                    "max_data_rate_rx": 150000, "max_data_rate_tx": 150000,
                    "rx_rcpi": -31, "tx_rcpi": 255,
                    "wifi_standard": "n", "stream_count": 1}]
            }]},
            {"uid": "client", "device_mac_address": "00:4B:12:69:4D:2C"},
        ]}
        mac = "00:4B:12:69:4D:2C"
        result = extract(payload, {mac: mac})[mac][0]
        self.assertEqual(result["wifi_rate_rx_mbps"], 0)
        self.assertEqual(result["wifi_rate_tx_mbps"], 71)
        self.assertEqual(result["wifi_rate_rx_max_mbps"], 150)
        self.assertEqual(result["wifi_rate_tx_max_mbps"], 150)
        self.assertEqual(result["wifi_mesh_signal_rx_raw"], -31)
        self.assertEqual(result["mesh_tx_rcpi_raw"], 255)
        self.assertEqual(result["mesh_wlan_link_radio_fields"], {
            "wifi_standard": "n", "stream_count": 1,
            "max_data_rate_rx": 150000, "max_data_rate_tx": 150000,
        })
        self.assertEqual(result["mesh_wlan_channel_radio_fields"], {
            "channel_width": "20 MHz",
        })
        self.assertNotIn("wifi_signal_dbm", result)

    def test_connected_ap_interface_band_is_client_scoped(self):
        mac = "20:6E:F1:02:62:D8"
        payload = {"nodes": [
            {"uid": "repeater", "mesh_role": "slave", "node_interfaces": [
                {"type": "WLAN", "current_channel": 7,
                 "current_channel_info": {"frequency_band": "2.4 GHz"},
                 "node_links": [{"uid": "l1", "state": "CONNECTED",
                                 "node_1_uid": "repeater", "node_2_uid": "client"}]},
                {"type": "WLAN", "current_channel": 104,
                 "current_channel_info": {"frequency_band": "5 GHz"},
                 "node_links": []}
            ]},
            {"uid": "client", "device_mac_address": mac},
        ]}
        result = extract(payload, {mac: mac})[mac][0]
        self.assertEqual(result["mesh_connected_ap_band_mhz"], 2400)
        self.assertEqual(result["mesh_wifi_channel"], 7)

    def test_connected_ap_schema_does_not_expose_unknown_values(self):
        mac = "20:6E:F1:02:62:D8"
        payload = {"nodes": [
            {"uid": "repeater", "mesh_role": "slave", "node_interfaces": [{
                "type": "WLAN", "current_channel": 7,
                "private_blob": "do not expose",
                "current_channel_info": {
                    "channel_width": "20 MHz",
                    "mystery_frequency": "sensitive text",
                    "frequency_mhz": 2442,
                    "secret": "do not expose",
                },
                "node_links": [{"uid": "l1", "state": "CONNECTED",
                    "node_1_uid": "repeater", "node_2_uid": "client"}],
            }]},
            {"uid": "client", "device_mac_address": mac},
        ]}
        result = extract(payload, {mac: mac})[mac][0]
        channel = result["mesh_wlan_connected_ap_channel_schema"]
        self.assertEqual(channel["frequency_mhz"]["value"], 2442)
        self.assertEqual(channel["channel_width"]["value"], "20 MHz")
        self.assertEqual(channel["mystery_frequency"], {"type": "string"})
        self.assertNotIn("secret", channel)
        self.assertNotIn("do not expose", str(result))

    def test_unmatched_client_and_disconnected_links_ignored(self):
        payload = {"nodes": [
            {"uid": "ap", "mesh_role": "master", "node_interfaces": [{
                "type": "WLAN", "node_links": [
                    {"uid": "x", "state": "DISCONNECTED", "node_1_uid": "ap",
                     "node_2_uid": "client", "rx_rcpi": -55}
                ]}]},
            {"uid": "client", "device_mac_address": "20:6E:F1:02:62:D8"},
        ]}
        self.assertEqual(extract(payload, {}), {})
