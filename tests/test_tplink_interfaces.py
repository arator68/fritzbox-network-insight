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


class TestEnrichment(unittest.TestCase):
    def setUp(self):
        from types import SimpleNamespace
        self.identity = SimpleNamespace(mac="02:11:22:33:44:55", model="TL-SG1024DE")

    def test_identity_only(self):
        host = {"mac": self.identity.mac.upper(), "connected_to": "router", "ip_address": "192.0.2.10"}
        before = host.copy()
        module.enrich_host(host, self.identity)
        self.assertEqual(host["detected_device_type"], "switch")
        self.assertEqual(host["device_model"], "TL-SG1024DE")
        self.assertEqual(host["detected_device_type_source"], "tplink_easy_smart_discovery")
        self.assertEqual({k: host[k] for k in before}, before)
        self.assertEqual(set(host) - set(before), {"detected_device_type", "detected_device_type_source", "device_manufacturer", "device_model"})

    def test_existing_evidence_preserved(self):
        for extra, identification in [({"mesh_role": "slave"}, None),
                                      ({"detected_device_type": "nas"}, None),
                                      ({}, {"device_type": "switch"})]:
            host = {"mac": self.identity.mac, **extra}
            before = host.copy()
            module.enrich_host(host, self.identity, identification)
            self.assertEqual(host, before)

    def test_mac_mismatch_and_missing_identity(self):
        host = {"mac": "02:11:22:33:44:56"}
        before = host.copy()
        for identity in (self.identity, None):
            module.enrich_host(host, identity)
            self.assertEqual(host, before)
