"""Regression tests for AVM Mesh infrastructure device_type fallback."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import sys
import types
import unittest

BASE = Path(__file__).resolve().parents[1] / "custom_components" / "fritzbox_network_insight" / "topology"
PACKAGE = "_mesh_type_test"
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
build_combined_topology = load("combined").build_combined_topology
build_topology_view = load("view_model").build_topology_view

MASTER = "04:B4:FE:18:79:65"
REPEATER = "BA:FC:7D:AE:37:B9"
SECONDARY = "E0:28:6D:C0:51:38"
CLIENT = "00:4B:12:69:4D:2C"

class MeshDeviceTypeTests(unittest.TestCase):
    def build(self, hosts=None):
        return build_combined_topology({}, {}, hosts or {}, {"nodes": [
            {"mac": MASTER, "mesh_role": "master"},
            {"mac": REPEATER, "mesh_role": "slave"},
            {"mac": SECONDARY, "mesh_role": "slave"},
            {"mac": CLIENT, "mesh_role": "unknown"},
        ], "links": []})

    def test_mesh_infrastructure_types(self):
        nodes = {n["mac"]: n for n in self.build()["nodes"]}
        self.assertEqual(nodes[MASTER]["device_type"], "router")
        self.assertEqual(nodes[REPEATER]["device_type"], "access_point")
        self.assertEqual(nodes[SECONDARY]["device_type"], "access_point")
        self.assertIsNone(nodes[CLIENT]["device_type"])
        self.assertEqual(nodes[REPEATER]["device_type_source"], "avm_mesh_role")

    def test_existing_classification_wins(self):
        nodes = {n["mac"]: n for n in self.build({
            REPEATER: {"name": "Repeater", "device_type": "switch"},
        })["nodes"]}
        self.assertEqual(nodes[REPEATER]["device_type"], "switch")
        self.assertIsNone(nodes[REPEATER]["device_type_source"])

    def test_view_exposes_type_and_provenance(self):
        snapshot = self.build()
        view = build_topology_view({"nodes": {n["mac"]: n for n in snapshot["nodes"]}})
        nodes = {n["mac"]: n for n in view["nodes"]}
        self.assertEqual(nodes[MASTER]["device_type"], "router")
        self.assertEqual(nodes[REPEATER]["device_type_source"], "avm_mesh_role")

if __name__ == "__main__":
    unittest.main()
