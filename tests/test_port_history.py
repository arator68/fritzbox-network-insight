"""Regression tests for durable FDB port history without Home Assistant installed."""
from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
import sys
import types
import unittest

BASE = Path(__file__).resolve().parents[1] / "custom_components" / "fritzbox_network_insight" / "topology"
PACKAGE = "_port_history_regression"

package = types.ModuleType(PACKAGE)
package.__path__ = [str(BASE)]
sys.modules[PACKAGE] = package

# Stub only the storage API; production uses Home Assistant's actual Store.
homeassistant = types.ModuleType("homeassistant")
core = types.ModuleType("homeassistant.core")
core.HomeAssistant = object
helpers = types.ModuleType("homeassistant.helpers")
storage = types.ModuleType("homeassistant.helpers.storage")


class FakeStore:
    saved: dict[str, dict] = {}

    def __init__(self, hass, version, key):
        self.key = key

    async def async_load(self):
        return self.saved.get(self.key)

    async def async_save(self, value):
        self.saved[self.key] = value


storage.Store = FakeStore
sys.modules.update({
    "homeassistant": homeassistant,
    "homeassistant.core": core,
    "homeassistant.helpers": helpers,
    "homeassistant.helpers.storage": storage,
})


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, BASE / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


load(f"{PACKAGE}.lldp_matcher", "lldp_matcher.py")
history = load(f"{PACKAGE}.port_history", "port_history.py")
SWITCH = "D4:D6:DF:0E:1B:54"
NAS = "90:09:D0:79:05:43"
PC = "04:D9:F5:7D:DD:8E"


def observed(mac, port):
    return {"source_mac": SWITCH, "target_mac": mac, "bridge_port": port,
            "vlan_id": "1", "interface_name": "gigabitEthernet 1/0/3"}


class PortHistoryTests(unittest.TestCase):
    def setUp(self):
        FakeStore.saved.clear()

    def test_absent_device_remains_with_original_timestamp(self):
        first = history.merge_port_history([], [observed(NAS, "49155")],
                                           observed_at="2026-11-08T09:00:00+00:00")
        second = history.merge_port_history(first, [],
                                            observed_at="2026-11-08T10:00:00+00:00")
        self.assertEqual(first, second)

    def test_repeated_observation_refreshes_timestamp(self):
        first = history.merge_port_history([], [observed(NAS, "49155")],
                                           observed_at="2026-11-08T09:00:00+00:00")
        second = history.merge_port_history(first, [observed(NAS, "49155")],
                                            observed_at="2026-11-08T10:00:00+00:00")
        self.assertEqual(len(second), 1)
        self.assertEqual(second[0]["last_seen"], "2026-11-08T10:00:00+00:00")

    def test_port_move_overwrites_last_known_port(self):
        first = history.merge_port_history([], [observed(NAS, "49155")],
                                           observed_at="2026-11-08T09:00:00+00:00")
        second = history.merge_port_history(first, [observed(NAS, "49157")],
                                            observed_at="2026-11-08T10:00:00+00:00")
        self.assertEqual(len(second), 1)
        self.assertEqual(second[0]["bridge_port"], "49157")

    def test_old_scan_cannot_revert_newer_port(self):
        first = history.merge_port_history([], [observed(NAS, "49157")],
                                           observed_at="2026-11-08T10:00:00+00:00")
        second = history.merge_port_history(first, [observed(NAS, "49155")],
                                            observed_at="2026-11-08T09:00:00+00:00")
        self.assertEqual(second, first)

    def test_restart_roundtrip_and_isolation(self):
        async def run():
            store = history.PortHistoryStore(None, "entry-one")
            records = history.merge_port_history([], [observed(NAS, "49155")],
                                                 observed_at="2026-11-08T09:00:00+00:00")
            await store.async_save(records)
            restored = await history.PortHistoryStore(None, "entry-one").async_load()
            other = await history.PortHistoryStore(None, "entry-two").async_load()
            self.assertEqual(restored, records)
            self.assertEqual(other, [])
        asyncio.run(run())

    def test_newest_entries_survive_limit(self):
        original = history.MAX_RECORDS
        history.MAX_RECORDS = 1
        try:
            old = history.merge_port_history([], [observed(NAS, "49155")],
                                             observed_at="2026-11-08T09:00:00+00:00")
            latest = history.merge_port_history(old, [observed(PC, "49157")],
                                                observed_at="2026-11-08T10:00:00+00:00")
            self.assertEqual([x["target_mac"] for x in latest], [PC])
        finally:
            history.MAX_RECORDS = original

    def test_rejects_naive_timestamp(self):
        self.assertEqual(history.sanitize_history([{
            **observed(NAS, "49155"), "last_seen": "2026-11-08T09:00:00",
            "evidence": "fdb_reachability",
        }]), [])


if __name__ == "__main__":
    unittest.main()
