"""Pure unit tests for standard BRIDGE-MIB FDB correlation."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / "custom_components/fritzbox_network_insight/discovery"
spec = importlib.util.spec_from_file_location("fdb_test_module", ROOT / "fdb.py")
assert spec and spec.loader
fdb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fdb)


class TestFdb(unittest.TestCase):
    def test_mac_suffix(self) -> None:
        self.assertEqual(fdb.mac_from_oid_suffix("4.180.254.24.121.101"), "04:B4:FE:18:79:65")
        self.assertIsNone(fdb.mac_from_oid_suffix("4.180.256.24.121.101"))

    def test_learned_only_and_bridge_mapping(self) -> None:
        suffix = "4.180.254.24.121.101"
        rows = fdb.correlate_fdb(
            [(suffix, "2"), ("1.2.3.4.5.6", "3")],
            [(suffix, "3"), ("1.2.3.4.5.6", "4")],
            [("2", "101")], [("101", "gigabitEthernet 1/0/2")],
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["bridge_port"], "2")
        self.assertEqual(rows[0]["interface_name"], "gigabitEthernet 1/0/2")
        self.assertEqual(rows[0]["connection"], "reachable_via_port")


if __name__ == "__main__":
    unittest.main()
