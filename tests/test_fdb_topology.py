"""Test FDB topology evidence without Home Assistant dependencies."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest

root = Path(__file__).resolve().parents[1] / "custom_components/fritzbox_network_insight/topology"
pkg = "test_fdb_topology_pkg"
module = types.ModuleType(pkg)
module.__path__ = [str(root)]
sys.modules[pkg] = module
for name in ("lldp_matcher", "fdb_model"):
    spec = importlib.util.spec_from_file_location(f"{pkg}.{name}", root / f"{name}.py")
    assert spec and spec.loader
    loaded = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = loaded
    spec.loader.exec_module(loaded)
model = sys.modules[f"{pkg}.fdb_model"]


class FdbTopologyTests(unittest.TestCase):
    def test_reachable_not_direct(self) -> None:
        entries = [{"mac": "90:09:D0:79:05:43", "bridge_port": "49155",
                    "vlan_id": "1", "interface_name": "gigabitEthernet 1/0/3",
                    "connection": "reachable_via_port"}]
        hosts = {"90:09:D0:79:05:43": {"name": "Synology NAS"}}
        rows = model.build_fdb_observations("D4:D6:DF:0E:1B:54", entries, hosts)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["target_name"], "Synology NAS")
        self.assertEqual(rows[0]["connection"], "reachable_via_port")
        self.assertEqual(rows[0]["evidence"], "fdb")

    def test_reject_invalid_or_unverified(self) -> None:
        rows = model.build_fdb_observations("D4:D6:DF:0E:1B:54",
            [{"mac": "01:02:03:04:05:06", "bridge_port": "2",
              "connection": "directly_connected"}], {})
        self.assertEqual(rows, [])


if __name__ == "__main__":
    unittest.main()
