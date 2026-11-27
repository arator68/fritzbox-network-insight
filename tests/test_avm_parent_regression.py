"""Regression tests for logical AVM parent selection."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "fritzbox_network_insight"
PKG = "_avm_parent_regression"
package = types.ModuleType(PKG)
package.__path__ = [str(ROOT)]
sys.modules[PKG] = package
device = types.ModuleType(PKG + ".device")
device.normalize_mac = lambda value: str(value).upper() if value else None
sys.modules[device.__name__] = device
spec = importlib.util.spec_from_file_location(PKG + ".connection_details", ROOT / "connection_details.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

ROUTER = "AA:00:00:00:00:01"
SWITCH = "AA:00:00:00:00:02"
CLIENT = "AA:00:00:00:00:03"
SECOND = "AA:00:00:00:00:04"

def mesh(source, target, port):
    return dict(source_mac=source, target_mac=target, source_interface=port,
                link_type="LAN", link_state="CONNECTED")

def lldp(source, target, port):
    return dict(source_mac=source, target_mac=target, source_port_id=port,
                connection="direct_confirmed")

class AvmParentTests(unittest.TestCase):
    def test_router_client_not_switch_uplink(self):
        snapshot = dict(nodes=[dict(mac=ROUTER, name="Router", mesh_role="master")],
                        mesh_links=[mesh(ROUTER, CLIENT, "LAN:4")],
                        reachable_via_port=[dict(source_mac=SWITCH, target_mac=CLIENT,
                            interface_name="port1", connection="reachable_via_port")])
        result = mod.connection_details(CLIENT, {"interface_type": "Ethernet"}, snapshot)
        self.assertEqual(result["connected_to_mac"], ROUTER)
        self.assertEqual(result["connection_evidence"], "avm_mesh")
        self.assertEqual(result["selected_connection"]["peer_port"], "LAN:4")

    def test_switch_master_not_secondary_router(self):
        snapshot = dict(nodes=[dict(mac=ROUTER, mesh_role="master", device_type="router"),
                               dict(mac=SECOND, mesh_role="slave", device_type="router")],
                        mesh_links=[mesh(ROUTER, SWITCH, "LAN:1"), mesh(SWITCH, SECOND, "port8")],
                        direct_links=[lldp(SWITCH, ROUTER, "port1"), lldp(SWITCH, SECOND, "port8")])
        result = mod.connection_details(SWITCH, {"interface_type": "Ethernet"}, snapshot)
        self.assertEqual(result["connected_to_mac"], ROUTER)
        self.assertEqual(result["connection_count"], 2)
        self.assertEqual(result["connected_to_port"], "port1")

    def test_wlan_ignores_lldp(self):
        snapshot = dict(direct_links=[lldp(SWITCH, CLIENT, "port8")])
        result = mod.connection_details(CLIENT, {"interface_type": "802.11"}, snapshot)
        self.assertIsNone(result["connected_to_mac"])
        self.assertIsNone(result["connected_to_port"])

    def test_master_has_no_parent(self):
        snapshot = dict(nodes=[dict(mac=ROUTER, mesh_role="master")],
                        mesh_links=[mesh(ROUTER, SWITCH, "LAN:1")],
                        direct_links=[lldp(SWITCH, ROUTER, "port1")])
        result = mod.connection_details(ROUTER, {"interface_type": "Ethernet"}, snapshot)
        self.assertIsNone(result["connected_to_mac"])

    def test_legacy_manual_link_is_not_evidence(self):
        result = mod.connection_details(CLIENT, {"interface_type": "Ethernet"}, {},
            [dict(source_mac=SWITCH, target_mac=CLIENT, bridge_port="8",
                  confirmation="user_confirmed")])
        self.assertIsNone(result["connected_to_mac"])

    def test_conflicting_single_lldp_does_not_replace_avm_master(self):
        snapshot = dict(nodes=[dict(mac=ROUTER, mesh_role="master")],
                        mesh_links=[mesh(ROUTER, CLIENT, "LAN:4")],
                        direct_links=[lldp(SWITCH, CLIENT, "port8")])
        result = mod.connection_details(CLIENT, {"interface_type": "Ethernet"}, snapshot)
        self.assertEqual(result["connected_to_mac"], ROUTER)
        self.assertEqual(result["selected_connection"]["peer_port"], "LAN:4")
        self.assertEqual(result["connection_evidence"], "avm_mesh")

if __name__ == "__main__":
    unittest.main()
