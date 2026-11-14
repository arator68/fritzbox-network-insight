"""Tests for safe central router device association."""
import sys
import types
import importlib.util
import unittest
from types import SimpleNamespace

# Load the small device-info helper without requiring a running HA instance.
from test_internal_graph import ROOT

class RouterDeviceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._old = {key: sys.modules.get(key) for key in (
            "homeassistant", "homeassistant.config_entries",
            "homeassistant.helpers", "homeassistant.helpers.device_registry",
            "homeassistant.helpers.entity_registry",
        )}
        ha = types.ModuleType("homeassistant")
        ha.__path__ = []
        config = types.ModuleType("homeassistant.config_entries")
        config.ConfigEntry = object
        helpers = types.ModuleType("homeassistant.helpers")
        helpers.__path__ = []
        registry = types.ModuleType("homeassistant.helpers.device_registry")
        registry.DeviceInfo = dict
        entity_registry = types.ModuleType("homeassistant.helpers.entity_registry")
        sys.modules.update({
            "homeassistant": ha, "homeassistant.config_entries": config,
            "homeassistant.helpers": helpers,
            "homeassistant.helpers.device_registry": registry,
            "homeassistant.helpers.entity_registry": entity_registry,
        })
        package_name = "_router_device_test"
        package = types.ModuleType(package_name)
        package.__path__ = [str(ROOT / "custom_components" / "fritzbox_network_insight")]
        sys.modules[package_name] = package
        const = types.ModuleType(f"{package_name}.const")
        const.DOMAIN = "fritzbox_network_insight"
        sys.modules[f"{package_name}.const"] = const
        cls._package_name = package_name
        spec = importlib.util.spec_from_file_location(
            f"{package_name}.router_device",
            ROOT / "custom_components" / "fritzbox_network_insight" / "router_device.py",
        )
        cls.module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.module
        spec.loader.exec_module(cls.module)

    @classmethod
    def tearDownClass(cls):
        for key in (f"{cls._package_name}.router_device", f"{cls._package_name}.const", cls._package_name):
            sys.modules.pop(key, None)
        for key, value in cls._old.items():
            if value is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = value

    def _resolve(self, hosts, address="192.168.178.1"):
        entry = SimpleNamespace(entry_id="entry-1", data={"host": address})
        coordinator = SimpleNamespace(data=hosts)
        return self.module.router_device_info(coordinator, entry)

    def test_unique_ip_matches_physical_mac(self):
        result = self._resolve({
            "AA:BB:CC:DD:EE:01": {"ip_address": "192.168.178.1"},
            "AA:BB:CC:DD:EE:02": {"ip_address": "192.168.178.2"},
        })
        self.assertEqual(result["identifiers"], {("fritzbox_network_insight", "AA:BB:CC:DD:EE:01")})

    def test_missing_router_keeps_separate_entry(self):
        result = self._resolve({"AA:BB:CC:DD:EE:02": {"ip_address": "192.168.178.2"}})
        self.assertEqual(result["identifiers"], {("fritzbox_network_insight", "entry-1")})

    def test_ambiguous_ip_keeps_separate_entry(self):
        result = self._resolve({
            "AA:BB:CC:DD:EE:01": {"ip_address": "192.168.178.1"},
            "AA:BB:CC:DD:EE:02": {"ip_address": "192.168.178.1"},
        })
        self.assertEqual(result["identifiers"], {("fritzbox_network_insight", "entry-1")})


    def test_migration_moves_only_owned_entities_and_removes_empty_old_device(self):
        old = SimpleNamespace(id="old", config_entries={"entry-1"})
        physical = SimpleNamespace(id="physical", config_entries={"entry-1"})
        owned = SimpleNamespace(entity_id="sensor.central", config_entry_id="entry-1", platform="fritzbox_network_insight")
        foreign = SimpleNamespace(entity_id="sensor.foreign", config_entry_id="other", platform="other")
        rows = [owned]
        updates = []
        removed = []
        device_registry = SimpleNamespace(
            async_get_device=lambda *, identifiers=None, connections=None: (
                old if identifiers == {("fritzbox_network_insight", "entry-1")}
                else physical
            ),
            async_remove_device=lambda device_id: removed.append(device_id),
        )
        entity_registry = SimpleNamespace(
            async_update_entity=lambda entity_id, **kwargs: (
                updates.append((entity_id, kwargs["device_id"])), rows.remove(owned)
            ),
        )
        self.module.dr.async_get = lambda hass: device_registry
        self.module.er.async_get = lambda hass: entity_registry
        self.module.er.async_entries_for_device = lambda reg, device_id: list(rows) if device_id == "old" else []
        entry = SimpleNamespace(entry_id="entry-1", data={"host": "192.168.178.1"})
        coordinator = SimpleNamespace(data={"AA:BB:CC:DD:EE:01": {"ip_address": "192.168.178.1"}})
        self.assertEqual(self.module.migrate_router_device(None, coordinator, entry), 1)
        self.assertEqual(updates, [("sensor.central", "physical")])
        self.assertEqual(removed, ["old"])

    def test_migration_preserves_old_device_if_foreign_entity_remains(self):
        old = SimpleNamespace(id="old", config_entries={"entry-1", "other"})
        physical = SimpleNamespace(id="physical", config_entries={"entry-1"})
        foreign = SimpleNamespace(entity_id="sensor.foreign", config_entry_id="other", platform="other")
        removed = []
        self.module.dr.async_get = lambda hass: SimpleNamespace(
            async_get_device=lambda *, identifiers=None, connections=None: (
                old if identifiers == {("fritzbox_network_insight", "entry-1")} else physical
            ),
            async_remove_device=lambda device_id: removed.append(device_id),
        )
        self.module.er.async_get = lambda hass: object()
        self.module.er.async_entries_for_device = lambda reg, device_id: [foreign] if device_id == "old" else []
        entry = SimpleNamespace(entry_id="entry-1", data={"host": "192.168.178.1"})
        coordinator = SimpleNamespace(data={"AA:BB:CC:DD:EE:01": {"ip_address": "192.168.178.1"}})
        self.assertEqual(self.module.migrate_router_device(None, coordinator, entry), 0)
        self.assertEqual(removed, [])


if __name__ == "__main__":
    unittest.main()
