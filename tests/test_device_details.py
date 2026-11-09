"""Regression tests for the pure device detail model."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "fritzbox_network_insight"
PACKAGE = "fritzbox_network_insight"
if PACKAGE not in sys.modules:
    package = types.ModuleType(PACKAGE)
    package.__path__ = [str(ROOT)]
    sys.modules[PACKAGE] = package


def _load(name):
    spec = importlib.util.spec_from_file_location(f"{PACKAGE}.{name}", ROOT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_load("device")
model = _load("device_details")


class TestDeviceDetails(unittest.TestCase):
    def test_identity_and_source_provenance(self):
        details = model.build_device_details(
            "d4:d6:df:0e:1b:54",
            {"snmp": {"device_type": "switch", "port": 1},
             "avm_mesh": {"device_type": "unknown", "name": "SG3428"}},
        )
        self.assertEqual(details.mac, "D4:D6:DF:0E:1B:54")
        self.assertEqual([x.source for x in details.values("device_type")], ["snmp", "avm_mesh"])
        self.assertEqual(details.values("port")[0].value, 1)

    def test_missing_values_omitted_but_false_and_zero_retained(self):
        details = model.build_device_details(
            "04:B4:FE:18:79:65",
            {"tr064": {"wifi_signal": None, "name": " ", "online": False, "speed": 0}},
        )
        self.assertFalse(details.available("wifi_signal"))
        self.assertFalse(details.available("name"))
        self.assertIs(details.values("online")[0].value, False)
        self.assertEqual(details.values("speed")[0].value, 0)

    def test_host_adapter_keeps_sources_and_omits_missing_fields(self):
        details = model.details_from_host({
            "mac": "04:B4:FE:18:79:65",
            "name": "fritz.box",
            "active": False,
            "dns_name": None,
            "mesh_role": "master",
            "raw": {"X_AVM-DE_Speed": "1000", "InterfaceType": "Ethernet"},
        })
        self.assertEqual(details.values("online")[0].value, False)
        self.assertEqual(details.values("online")[0].source, "tr064")
        self.assertEqual(details.values("mesh_role")[0].source, "avm_mesh")
        self.assertEqual(details.values("lan_speed_mbps")[0].value, "1000")
        self.assertFalse(details.available("dns_name"))
        self.assertFalse(details.available("wifi_signal"))

    def test_snmp_only_actual_nonsecret_observations(self):
        details = model.build_device_details("D4:D6:DF:0E:1B:54", {})
        model.add_snmp_details(details, {
            "protocols": ["snmp"], "sys_name": "SG3428",
            "fdb_entry_count": "22", "auth_password": "SECRET",
            "last_run": "2026-11-09T08:00:00+00:00",
        })
        self.assertEqual(details.values("snmp_system_name")[0].source, "snmp_v3")
        self.assertEqual(details.values("fdb_entry_count")[0].value, "22")
        self.assertFalse(details.available("auth_password"))
        self.assertFalse(details.available("snmp_system_description"))

    def test_lldp_and_mesh_do_not_claim_physical_cable(self):
        details = model.build_device_details("D4:D6:DF:0E:1B:54", {})
        model.add_mesh_link_details(details, [{
            "source_mac": "D4:D6:DF:0E:1B:54",
            "target_mac": "04:B4:FE:18:79:65", "link_type": "lan",
        }])
        model.add_lldp_link_details(details, {
            "D4:D6:DF:0E:1B:54": [{
                "target_mac": "04:B4:FE:18:79:65",
                "source_port_id": "gigabitEthernet 1/0/1",
                "target_port_id": "LAN 1", "match_status": "matched",
                "observed_at": "2026-11-09T08:00:00+00:00",
            }]
        })
        self.assertEqual(details.values("mesh_reported_link")[0].source, "avm_mesh")
        self.assertEqual(details.values("lldp_observed_link")[0].source, "lldp")
        self.assertFalse(details.available("physical_cable"))

    def test_invalid_identity_and_missing_source_rejected(self):
        with self.assertRaises(ValueError):
            model.build_device_details("invalid", {"tr064": {"name": "x"}})
        with self.assertRaises(ValueError):
            model.build_device_details("04:B4:FE:18:79:65", {"": {"name": "x"}})


if __name__ == "__main__":
    unittest.main()
