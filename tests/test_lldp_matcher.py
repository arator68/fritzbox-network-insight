"""LLDP chassis matching must never guess links from names or vendors."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).resolve().parents[1] / "custom_components/fritzbox_network_insight/topology/lldp_matcher.py"
spec = importlib.util.spec_from_file_location("lldp_matcher", PATH)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TestLldpMatcher(unittest.TestCase):
    def setUp(self) -> None:
        self.hosts = {
            "04:B4:FE:18:79:65": {
                "mac": "04:B4:FE:18:79:65",
                "name": "FRITZ!Box 7590 AX",
                "ip_address": "192.168.178.1",
            },
        }

    def test_exact_chassis_mac_match(self) -> None:
        neighbor = {"chassis_id_subtype": "4", "chassis_id": "04-b4-fe-18-79-65", "local_port_number": "1"}
        result = module.match_lldp_neighbors([neighbor], self.hosts)[0]
        self.assertEqual(result["match_status"], "matched")
        self.assertEqual(result["matched_mac"], "04:B4:FE:18:79:65")
        self.assertEqual(result["local_port_number"], "1")

    def test_unknown_chassis_stays_unmatched_despite_same_name(self) -> None:
        result = module.match_lldp_neighbors([{
            "chassis_id_subtype": "4", "chassis_id": "F0:28:6D:C0:51:38",
            "system_name": "FRITZ!Box 7590 AX",
        }], self.hosts)[0]
        self.assertEqual(result["match_status"], "unmatched")
        self.assertNotIn("matched_mac", result)

    def test_non_mac_subtype_cannot_match(self) -> None:
        result = module.match_lldp_neighbors([{
            "chassis_id_subtype": "7", "chassis_id": "04:B4:FE:18:79:65",
        }], self.hosts)[0]
        self.assertEqual(result["match_status"], "unmatched")

    def test_duplicate_mac_is_ambiguous(self) -> None:
        hosts = {
            "one": {"mac": "04:B4:FE:18:79:65"},
            "two": {"mac": "04:B4:FE:18:79:65"},
        }
        result = module.match_lldp_neighbors([{
            "chassis_id_subtype": "4", "chassis_id": "04:B4:FE:18:79:65",
        }], hosts)[0]
        self.assertEqual(result["match_status"], "ambiguous")


if __name__ == "__main__":
    unittest.main()
