"""Regression checks for router LAN sensors with missing TR-064 interface type."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "fritzbox_network_insight"
PKG = "_router_lldp_test"


def module(name, **attributes):
    value = types.ModuleType(name)
    for key, item in attributes.items():
        setattr(value, key, item)
    sys.modules[name] = value
    return value


class RouterLldpSensorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.previous = {key: value for key, value in sys.modules.items()
                        if key.startswith("homeassistant") or key.startswith(PKG)}
        module("homeassistant")
        module("homeassistant.components")
        module("homeassistant.components.sensor", SensorEntity=object)
        module("homeassistant.helpers")
        module("homeassistant.helpers.device_registry", DeviceInfo=dict)
        class CoordinatorEntity:
            def __class_getitem__(cls, item):
                return cls

            def __init__(self, coordinator):
                self.coordinator = coordinator
        module("homeassistant.helpers.update_coordinator", CoordinatorEntity=CoordinatorEntity)
        package = module(PKG)
        package.__path__ = [str(ROOT)]
        module(f"{PKG}.const", DOMAIN="fritzbox_network_insight")
        module(f"{PKG}.coordinator", FritzBoxDataUpdateCoordinator=object)
        module(f"{PKG}.connection_details", connection_details=lambda mac, host, snapshot, manual: snapshot["resolved"])
        spec = importlib.util.spec_from_file_location(f"{PKG}.device_connection_sensors", ROOT / "device_connection_sensors.py")
        cls.loaded = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.loaded
        spec.loader.exec_module(cls.loaded)

    @classmethod
    def tearDownClass(cls):
        for key in list(sys.modules):
            if key.startswith(PKG) or (key.startswith("homeassistant") and key not in cls.previous):
                sys.modules.pop(key, None)
        sys.modules.update(cls.previous)

    def reading(self, field, kind="unknown", evidence="lldp_last_observed", peer_type="switch", links=1, telemetry=None):
        mac = "04:B4:FE:18:79:65"
        peer = "D4:D6:DF:0E:1B:54"
        link = {"connected_to_mac": peer, "connected_to": "SG3428",
                "peer_port": "gigabitEthernet 1/0/1", "evidence": evidence}
        snapshot = {"nodes": [{"mac": peer, "device_type": peer_type}],
                    "resolved": {"connection_type": kind, "connections": [link] * links,
                                 "connected_to": "SG3428", "connected_to_mac": peer,
                                 "connection_evidence": evidence}}
        switch_details = SimpleNamespace(values=lambda key: [SimpleNamespace(value=item) for item in (telemetry or [])] if key == "snmp_port_telemetry" else [])
        coordinator = SimpleNamespace(data={mac: {"interface_type": None}},
                                      manual_links=[], device_details={peer: switch_details},
                                      get_combined_topology_snapshot=lambda: snapshot)
        sensor = self.loaded.FritzBoxDeviceConnectionSensor(coordinator, mac, field)
        return sensor._reading

    def test_unique_lldp_establishes_router_lan(self):
        self.assertEqual(self.reading("type")[0], "lan")
        self.assertEqual(self.reading("peer")[0], "SG3428")
        self.assertEqual(self.reading("evidence")[0], "lldp_last_observed")

    def test_switch_peer_port_from_lldp(self):
        value, attrs = self.reading("switch_port")
        self.assertEqual(value, "1")
        self.assertEqual(attrs["direct_connection"], "confirmed")

    def test_lldp_does_not_invent_speed(self):
        self.assertIsNone(self.reading("port_speed")[0])

    def test_exact_lldp_switch_port_speed(self):
        value, attrs = self.reading("port_speed", telemetry=[{"interface_name": "gigabitEthernet 1/0/1", "reported_speed_mbps": 1000, "speed_source": "ifHighSpeed"}])
        self.assertEqual(value, 1000)
        self.assertEqual(attrs["speed_source"], "ifHighSpeed")

    def test_no_speed_for_other_or_ambiguous_ports(self):
        wrong = {"interface_name": "gigabitEthernet 1/0/2", "reported_speed_mbps": 1000}
        self.assertIsNone(self.reading("port_speed", telemetry=[wrong])[0])
        same = {"interface_name": "gigabitEthernet 1/0/1", "reported_speed_mbps": 1000}
        self.assertIsNone(self.reading("port_speed", telemetry=[same, same])[0])

    def test_no_inference_from_unconfirmed_or_ambiguous_links(self):
        self.assertIsNone(self.reading("type", evidence="user_confirmed")[0])
        self.assertIsNone(self.reading("type", links=2)[0])

    def test_no_switch_port_for_non_switch_peer(self):
        self.assertIsNone(self.reading("switch_port", peer_type="router")[0])

    def test_wlan_is_not_overridden(self):
        self.assertEqual(self.reading("type", kind="wlan")[0], "wlan")
        self.assertIsNone(self.reading("switch_port", kind="wlan")[0])


if __name__ == "__main__":
    unittest.main()
