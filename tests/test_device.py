"""Tests for FRITZ!Box host normalization."""
import unittest

from custom_components.fritzbox_network_insight.device import (
    as_bool,
    normalize_host,
    normalize_mac,
)


class TestNormalizeMac(unittest.TestCase):
    def test_normalizes_separators_and_case(self):
        self.assertEqual(normalize_mac("04-b4-fe-18-79-65"), "04:B4:FE:18:79:65")

    def test_rejects_invalid_mac(self):
        self.assertIsNone(normalize_mac("not-a-mac"))


class TestNormalizeHost(unittest.TestCase):
    def test_maps_raw_tr064_fields(self):
        host = normalize_host({
            "MACAddress": "04:b4:fe:18:79:65",
            "HostName": "router",
            "IPAddress": "192.168.178.1",
            "InterfaceType": "Ethernet",
            "Active": "1",
        })
        self.assertIsNotNone(host)
        self.assertEqual(host["mac"], "04:B4:FE:18:79:65")
        self.assertEqual(host["name"], "router")
        self.assertEqual(host["ip_address"], "192.168.178.1")
        self.assertIs(host["active"], True)

    def test_ignores_entries_without_valid_mac(self):
        self.assertIsNone(normalize_host({"HostName": "invalid"}))


class TestAsBool(unittest.TestCase):
    def test_known_values(self):
        self.assertIs(as_bool("1"), True)
        self.assertIs(as_bool("0"), False)
        self.assertIs(as_bool("unknown"), None)


if __name__ == "__main__":
    unittest.main()
