"""Unit tests for the conservative LLDP topology model."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1] / "custom_components/fritzbox_network_insight/topology"
package = types.ModuleType("topology")
package.__path__ = [str(ROOT)]
sys.modules.setdefault("topology", package)


def load(name: str) -> object:
    spec = importlib.util.spec_from_file_location(f"topology.{name}", ROOT / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


load("lldp_matcher")
model = load("model")


class TestTopologyModel(unittest.TestCase):
    def test_confirmed_lldp_link(self) -> None:
        links = model.build_lldp_links("D4:D6:0F:0E:1B:54", [{
            "local_port_number": "1",
            "local_port_id": "gigabitEthernet 1/0/1",
            "chassis_id_subtype": "4",
            "chassis_id": "04:B4:FE:18:79:65",
            "matched_mac": "04:B4:FE:18:79:65",
            "matched_name": "FRITZ!Box",
            "match_status": "matched",
            "port_id": "04:B4:FE:18:79:65",
        }], observed_at="2026-11-07T12:00:00+00:00")
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]["target_mac"], "04:B4:FE:18:79:65")
        self.assertEqual(links[0]["evidence"], "lldp")
        self.assertEqual(links[0]["source_port_number"], "1")
        self.assertEqual(links[0]["observed_at"], "2026-11-07T12:00:00+00:00")

    def test_unknown_is_not_invented(self) -> None:
        links = model.build_lldp_links("D4:D6:0F:0E:1B:54", [{
            "local_port_number": "8",
            "chassis_id_subtype": "4",
            "chassis_id": "F0:28:6D:C0:51:38",
            "match_status": "unmatched",
        }])
        self.assertEqual(links[0]["match_status"], "unmatched")
        self.assertIsNone(links[0]["target_mac"])

    def test_invalid_observation_is_not_a_link(self) -> None:
        self.assertEqual(model.build_lldp_links("invalid", []), [])
        self.assertEqual(model.build_lldp_links("D4:D6:0F:0E:1B:54", [{
            "local_port_number": "2", "chassis_id_subtype": "7",
            "chassis_id": "04:B4:FE:18:79:65",
        }]), [])

    def test_snapshot_is_explicitly_historical(self) -> None:
        snapshot = model.topology_snapshot({}, {})
        self.assertEqual(snapshot["link_count"], 0)
        self.assertEqual(snapshot["evidence"], "last_manual_lldp_observation")


if __name__ == "__main__":
    unittest.main()
