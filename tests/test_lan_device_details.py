"""Tests for conservative FDB-to-IF-MIB device detail correlation."""
import importlib.util
import json
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


def load(name):
    spec = importlib.util.spec_from_file_location(f"{PACKAGE}.{name}", ROOT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


load("device")
model = load("device_details")
join = load("lan_device_details")
SWITCH = "D4:D6:DF:0E:1B:54"
DEVICE = "20:6E:F1:02:62:D8"


class TestLanPortDetails(unittest.TestCase):
    def test_existing_fdb_mapping_joins_measured_port(self):
        devices = {DEVICE: model.build_device_details(DEVICE, {})}
        discovery = {SWITCH: {
            "port_telemetry_status": "ok",
            "port_telemetry": json.dumps([
                {"if_index": 49159, "interface_name": "gigabitEthernet 1/0/7",
                 "reported_speed_mbps": 100, "speed_source": "ifHighSpeed",
                 "oper_status": "up"}]),
            "last_run": "2026-11-09T07:59:12+00:00",
        }}
        fdb = {SWITCH: [{
            "target_mac": DEVICE, "if_index": "49159",
            "interface_name": "gigabitEthernet 1/0/7",
            "bridge_port": "7", "connection": "reachable_via_port",
        }]}
        join.add_lan_port_details(devices, discovery, fdb)
        item = devices[DEVICE].values("lan_switch_port")[0]
        self.assertEqual(item.value["reported_speed_mbps"], 100)
        self.assertEqual(item.value["connection"], "reachable_via_port")
        self.assertEqual(item.source, "snmp_v3_if_mib+fdb")
        self.assertNotIn("directly_connected", item.value)

    def test_no_match_or_failed_telemetry_does_not_guess(self):
        devices = {DEVICE: model.build_device_details(DEVICE, {})}
        fdb = {SWITCH: [{"target_mac": DEVICE, "if_index": "49159",
                         "connection": "reachable_via_port"}]}
        join.add_lan_port_details(devices, {SWITCH: {
            "port_telemetry_status": "unavailable", "port_telemetry": "[]",
        }}, fdb)
        self.assertFalse(devices[DEVICE].available("lan_switch_port"))
        join.add_lan_port_details(devices, {SWITCH: {
            "port_telemetry_status": "ok",
            "port_telemetry": '[{"if_index":49160,"interface_name":"port8","reported_speed_mbps":1000}]',
        }}, fdb)
        self.assertFalse(devices[DEVICE].available("lan_switch_port"))


if __name__ == "__main__":
    unittest.main()
