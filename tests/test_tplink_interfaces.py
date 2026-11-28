"""Tests for Easy Smart interface selection."""
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / "custom_components/fritzbox_network_insight/discovery/tplink_interfaces.py"
spec = importlib.util.spec_from_file_location("tplink_interfaces_test", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TestInterfaces(unittest.TestCase):
    def test_enabled_unique_ipv4(self):
        adapter = {"enabled": True, "mac": "02:11:22:33:44:55",
                   "ipv4": [{"address": "192.0.2.10"}, {"address": "192.0.2.10"},
                            {"address": "127.0.0.1"}, {"address": "169.254.1.1"},
                            {"address": "0.0.0.0"}, {"address": "invalid"}]}
        self.assertEqual(module.select_interfaces([adapter]),
                         [("192.0.2.10", bytes.fromhex("021122334455"))])

    def test_disabled_or_invalid_mac(self):
        for enabled, mac in [(False, "02:11:22:33:44:55"), (True, None),
                             (True, "ff:ff:ff:ff:ff:ff"), (True, "00:00:00:00:00:00")]:
            self.assertEqual(module.select_interfaces([{"enabled": enabled, "mac": mac,
                "ipv4": [{"address": "192.0.2.10"}]}]), [])

    def test_multiple_interfaces(self):
        adapters = [{"enabled": True, "mac": "02:11:22:33:44:55",
                     "ipv4": [{"address": ip}]} for ip in ("192.0.2.10", "198.51.100.10")]
        self.assertEqual(len(module.select_interfaces(adapters)), 2)
