"""WLAN connection metadata must not infer topology or radio bands."""
import importlib.util
import pathlib
import sys
import types
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1] / "custom_components" / "fritzbox_network_insight"
PACKAGE = "wlan_metadata_test_package"
pkg = types.ModuleType(PACKAGE)
pkg.__path__ = [str(ROOT)]
sys.modules.setdefault(PACKAGE, pkg)


def load(name):
    spec = importlib.util.spec_from_file_location(f"{PACKAGE}.{name}", ROOT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


details_module = load("device_details")
module = load("wlan_connection_metadata")


class WlanConnectionMetadataTests(unittest.TestCase):
    MAC = "68:F6:3B:6B:48:0A"
    PEER = "66:B5:8D:22:C9:0C"

    def test_explicit_wlan_role_band_and_connected_peer(self):
        details = details_module.DeviceDetails(self.MAC)
        details.add("wifi_frequency_band_mhz", 5000, source="tr064")
        details.add("mesh_reported_link", {
            "peer_mac": self.PEER, "link_type": "WLAN", "link_state": "CONNECTED",
        }, source="avm_mesh")
        host = {"active": True, "interface_type": "802.11"}
        mesh = {"aliases": {self.PEER: self.PEER},
                "nodes": [{"mac": self.PEER, "name": "Repeater-Flur.koch.local"}]}
        observed = module.connection_metadata(self.MAC, host, details, {}, mesh)
        self.assertEqual(observed["role"]["value"], "WLAN-Client")
        self.assertEqual(observed["band"]["value"], "5 GHz")
        self.assertEqual(observed["peer"]["value"], "Repeater-Flur.koch.local")
        self.assertEqual(observed["peer"]["connection_scope"], "avm_reported_wlan_link")

    def test_no_guesses_from_channel_or_disconnected_links(self):
        details = details_module.DeviceDetails(self.MAC)
        details.add("mesh_wifi_channel", 104, source="avm_mesh")
        details.add("mesh_reported_link", {
            "peer_mac": self.PEER, "link_type": "WLAN", "link_state": "DISCONNECTED",
        }, source="avm_mesh")
        observed = module.connection_metadata(
            self.MAC, {"active": True, "interface_type": "802.11"}, details, {}, {}
        )
        self.assertEqual(set(observed), {"role"})

    def test_channel_104_derives_five_ghz_with_provenance(self):
        details = details_module.DeviceDetails(self.MAC)
        details.add("mesh_peer_interface_channel", 104, source="avm_mesh_radio")
        observed = module.connection_metadata(
            self.MAC, {"active": True, "interface_type": "802.11"}, details, {}, {}
        )
        self.assertEqual(observed["band"]["value"], "5 GHz")
        self.assertEqual(observed["band"]["source"], "derived_from_wlan_channel")
        self.assertEqual(observed["band"]["channel"], 104)
        self.assertEqual(observed["band"]["source_field"], "mesh_peer_interface_channel")

    def test_explicit_band_takes_precedence_over_channel(self):
        details = details_module.DeviceDetails(self.MAC)
        details.add("wifi_frequency_band_mhz", 5000, source="tr064")
        details.add("mesh_peer_interface_channel", 104, source="avm_mesh_radio")
        observed = module.connection_metadata(
            self.MAC, {"active": True, "interface_type": "802.11"}, details, {}, {}
        )
        self.assertEqual(observed["band"]["source"], "tr064")

    def test_ambiguous_channel_is_not_guessed(self):
        details = details_module.DeviceDetails(self.MAC)
        details.add("mesh_peer_interface_channel", 7, source="avm_mesh_radio")
        observed = module.connection_metadata(
            self.MAC, {"active": True, "interface_type": "802.11"}, details, {}, {}
        )
        self.assertNotIn("band", observed)

    def test_offline_and_non_wlan_have_no_connection_metadata(self):
        details = details_module.DeviceDetails(self.MAC)
        for host in ({"active": False, "interface_type": "802.11"},
                     {"active": True, "interface_type": "Ethernet"}):
            self.assertEqual(
                module.connection_metadata(self.MAC, host, details, {}, {}), {}
            )


if __name__ == "__main__":
    unittest.main()
