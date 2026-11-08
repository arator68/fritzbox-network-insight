"""Tests for evidence-preserving per-device topology resolution."""
import unittest

from test_internal_graph import _load_module, PACKAGE

resolve_device_connections = _load_module(
    f"{PACKAGE}.device_connections", "device_connections.py"
).resolve_device_connections


SWITCH = "D4:D6:DF:0E:1B:54"
ROUTER = "04:B4:FE:18:79:65"
CLIENT = "AA:BB:CC:DD:EE:01"
NAS = "AA:BB:CC:DD:EE:02"


class DeviceConnectionsTests(unittest.TestCase):
    def test_fdb_only_never_creates_physical_link(self):
        graph = {
            "nodes": {NAS: {"name": "NAS"}},
            "lan_port_memberships": [{
                "switch_mac": SWITCH, "bridge_port": "49155",
                "vlan_id": "1", "interface_names": ["gigabitEthernet 1/0/3"],
                "members": [{"mac": NAS}],
            }],
        }
        result = resolve_device_connections(graph)
        self.assertEqual(result[0]["connection_type"], "reachable_via_port")
        self.assertFalse(result[0]["physical_link_confirmed"])
        self.assertEqual(result[0]["bridge_port"], "49155")

    def test_wlan_parent_takes_precedence_over_fdb(self):
        graph = {
            "lan_port_memberships": [{
                "switch_mac": SWITCH, "bridge_port": "49153",
                "vlan_id": "1", "members": [{"mac": CLIENT}],
            }],
            "wlan_attachments": {CLIENT: {"parent_mac": ROUTER}},
        }
        result = resolve_device_connections(graph)[0]
        self.assertEqual(result["connection_type"], "wlan")
        self.assertEqual(result["parent_mac"], ROUTER)
        self.assertFalse(result["physical_link_confirmed"])

    def test_history_only_is_historical_not_online(self):
        graph = {"port_history": [{
            "target_mac": NAS, "source_mac": SWITCH,
            "bridge_port": "49155", "last_seen": "2026-11-08T09:00:00+00:00",
        }]}
        result = resolve_device_connections(graph)[0]
        self.assertEqual(result["status"], "historical")
        self.assertEqual(result["connection_type"], "last_known_port")
        self.assertFalse(result["physical_link_confirmed"])

    def test_confirmed_lldp_is_physical(self):
        graph = {"links": [{
            "source_mac": SWITCH, "target_mac": ROUTER,
            "medium": "lan", "evidence": "lldp",
        }]}
        result = resolve_device_connections(graph)[0]
        self.assertTrue(result["physical_link_confirmed"])
        self.assertEqual(result["parent_mac"], SWITCH)
        self.assertEqual(result["evidence"], "lldp")

    def test_avm_logical_lan_does_not_confirm_cable(self):
        graph = {"links": [{
            "source_mac": SWITCH, "target_mac": ROUTER,
            "medium": "lan", "evidence": "avm_mesh",
        }]}
        self.assertEqual(resolve_device_connections(graph), [])


if __name__ == "__main__":
    unittest.main()
