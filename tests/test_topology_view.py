"""Tests for map projection; no Home Assistant runtime required."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest

BASE = Path(__file__).resolve().parents[1] / "custom_components" / "fritzbox_network_insight" / "topology"
PACKAGE = "_topology_view_test"
package = types.ModuleType(PACKAGE)
package.__path__ = [str(BASE)]
sys.modules[PACKAGE] = package

def load(name):
    spec = importlib.util.spec_from_file_location(f"{PACKAGE}.{name}", BASE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

load("lldp_matcher")
build_topology_view = load("view_model").build_topology_view

ROUTER = "04:B4:FE:18:79:65"
SWITCH = "D4:D6:DF:0E:1B:54"
DOWNSTREAM = "EC:75:0C:C2:68:F7"
SERVER = "2C:CF:67:EF:3B:60"
REPEATER = "BA:FC:7D:AE:37:B9"

class ViewModelTests(unittest.TestCase):
    def test_mesh_repeater_without_uplink_stays_visible(self):
        graph = {"nodes": {
            ROUTER: {"mac": ROUTER, "name": "fritz.box"},
            REPEATER: {"mac": REPEATER, "name": "Repeater-Kueche", "mesh_role": "repeater"},
        }, "links": []}
        view = build_topology_view(graph)
        self.assertEqual(len(view["nodes"]), 2)
        self.assertEqual(view["edges"], [])

    def test_confirmed_switch_and_fdb_branch_not_fabricated_cable(self):
        graph = {
            "nodes": {mac: {"mac": mac} for mac in (ROUTER, SWITCH, DOWNSTREAM, SERVER)},
            "links": [
                {"source_mac": SWITCH, "target_mac": ROUTER,
                 "medium": "lan", "evidence": "lldp", "details": {}},
                {"source_mac": SWITCH, "target_mac": DOWNSTREAM,
                 "medium": "lan", "evidence": "user_confirmed", "details": {"bridge_port": "49154"}},
            ],
            "mesh_lan_observations": [
                {"source_mac": ROUTER, "target_mac": SERVER},
            ],
            "graph_branches": [{
                "parent_mac": SWITCH, "switch_mac": DOWNSTREAM,
                "members": [{"mac": SERVER, "downstream_port_known": False}],
            }],
        }
        view = build_topology_view(graph)
        self.assertEqual(view["edge_count"], 2)
        self.assertEqual(len(view["mesh_lan_observations"]), 1)
        self.assertEqual(view["branches"][0]["members"][0]["mac"], SERVER)
        self.assertFalse(view["branches"][0]["members"][0]["physical_link_confirmed"])
        self.assertFalse(any(e["target"] == SERVER for e in view["edges"]))

    def test_wlan_mesh_edge_is_not_confirmed_lan(self):
        view = build_topology_view({
            "nodes": {},
            "links": [{"source_mac": ROUTER, "target_mac": REPEATER,
                       "medium": "wlan", "evidence": "avm_mesh", "details": {}}],
        })
        self.assertEqual(view["edges"][0]["kind"], "mesh_wlan")
        self.assertFalse(view["edges"][0]["physical_link_confirmed"])

if __name__ == "__main__":
    unittest.main()
