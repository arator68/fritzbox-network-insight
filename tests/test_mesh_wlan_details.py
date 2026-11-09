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
                    "cur_data_rate_rx": 86000, "cur_data_rate_tx": 68000}]
            }]},
            {"uid": "client", "device_mac_address": "20:6E:F1:02:62:D8",
             "node_interfaces": []},
        ]}
        original = copy.deepcopy(payload)
        data = extract(payload, {"20:6E:F1:02:62:D8": "20:6E:F1:02:62:D8"})
        self.assertEqual(payload, original)
        radio = data["20:6E:F1:02:62:D8"][0]
        self.assertEqual(radio["mesh_rx_rcpi_raw"], -55)
        self.assertEqual(radio["mesh_rate_rx_kbps"], 86000)
        self.assertEqual(radio["mesh_wifi_channel"], 11)
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
