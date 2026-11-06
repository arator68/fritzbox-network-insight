"""Tests for FRITZ!Box host normalization without importing Home Assistant."""
import importlib.util
from pathlib import Path
import unittest

DEVICE_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "fritzbox_network_insight"
    / "device.py"
)
SPEC = importlib.util.spec_from_file_location("fritzbox_network_device", DEVICE_PATH)
assert SPEC is not None and SPEC.loader is not None
DEVICE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DEVICE)

normalize_mac = DEVICE.normalize_mac
normalize_host = DEVICE.normalize_host
as_bool = DEVICE.as_bool


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
