"""Combined topology model tests without Home Assistant runtime."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest

root = Path(__file__).resolve().parents[1] / "custom_components/fritzbox_network_insight/topology"
pkg = "test_combined_topology_pkg"
package = types.ModuleType(pkg)
package.__path__ = [str(root)]
sys.modules[pkg] = package
for name in ("lldp_matcher", "combined"):
    spec = importlib.util.spec_from_file_location(f"{pkg}.{name}", root / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
combined = sys.modules[f"{pkg}.combined"]


class CombinedTopologyTests(unittest.TestCase):
    def test_keeps_direct_and_reachable_separate(self) -> None:
        source = "D4:D6:DF:0E:1B:54"
        target = "04:B4:FE:18:79:65"
        lldp = {source: [{
            "target_mac": target, "match_status": "matched",
            "source_port_number": "1", "evidence": "lldp",
        }]}
        fdb = {source: [{
            "target_mac": target, "bridge_port": "49153",
            "vlan_id": "1", "connection": "reachable_via_port",
        }, {
            "target_mac": "90:09:D0:79:05:43", "bridge_port": "49155",
            "vlan_id": "1", "connection": "reachable_via_port",
        }]}
        result = combined.build_combined_topology(lldp, fdb, {})
        self.assertEqual(result["direct_link_count"], 1)
        self.assertEqual(result["reachability_count"], 2)
        self.assertEqual(result["node_count"], 3)
        self.assertTrue(all(x["connection"] == "direct_confirmed"
                            for x in result["direct_links"]))
        self.assertTrue(all(x["connection"] == "reachable_via_port"
                            for x in result["reachable_via_port"]))

    def test_unmatched_lldp_never_creates_direct_link(self) -> None:
        result = combined.build_combined_topology({
            "D4:D6:DF:0E:1B:54": [{
                "target_mac": "04:B4:FE:18:79:65",
                "match_status": "unmatched",
            }]
        }, {}, {})
        self.assertEqual(result["direct_link_count"], 0)

    def test_multiple_switch_sources_do_not_collide(self) -> None:
        entries = [{
            "target_mac": "90:09:D0:79:05:43",
            "bridge_port": "49155", "vlan_id": "1",
            "connection": "reachable_via_port",
        }]
        result = combined.build_combined_topology({}, {
            "D4:D6:DF:0E:1B:54": entries,
            "AA:BB:CC:DD:EE:FF": entries,
        }, {})
        self.assertEqual(result["fdb_source_count"], 2)
        self.assertEqual(result["reachability_count"], 2)


if __name__ == "__main__":
    unittest.main()
