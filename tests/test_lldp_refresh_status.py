"""Regression tests: LLDP walk status must distinguish errors from empty results."""
import asyncio
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components/fritzbox_network_insight/discovery/lldp.py"
)
spec = importlib.util.spec_from_file_location("lldp_status_under_test", MODULE_PATH)
lldp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lldp)


class LldpStatusTests(unittest.IsolatedAsyncioTestCase):
    async def _read(self, *, fail=False, neighbor=False):
        module = types.ModuleType("pysnmp.hlapi.v3arch.asyncio")
        module.ContextData = lambda: None
        module.ObjectIdentity = lambda value: value
        module.ObjectType = lambda value: value

        async def walk_cmd(engine, user, target, context, obj, **kwargs):
            if fail:
                yield ("timeout", None, None, [])
                return
            if obj == lldp.LOCAL_PORT_ID:
                yield (None, None, None, [(lldp.LOCAL_PORT_ID + ".16", "gigabitEthernet 1/0/16")])
            elif neighbor:
                base = lldp.REMOTE_BASE
                yield (None, None, None, [
                    (base + ".4.1.16.1", "4"),
                    (base + ".5.1.16.1", "2C:CF:67:EF:3B:60"),
                    (base + ".7.1.16.1", "eth0"),
                ])
        module.walk_cmd = walk_cmd
        with patch.dict(sys.modules, {"pysnmp": types.ModuleType("pysnmp"),
                                      "pysnmp.hlapi": types.ModuleType("pysnmp.hlapi"),
                                      "pysnmp.hlapi.v3arch": types.ModuleType("pysnmp.hlapi.v3arch"),
                                      "pysnmp.hlapi.v3arch.asyncio": module}):
            return await lldp.async_read_lldp_with_status(None, None, None)

    async def test_empty_success_is_not_failure(self):
        result = await self._read()
        self.assertEqual(result, {"status": "ok", "neighbors": []})

    async def test_failed_walk_is_not_empty_success(self):
        result = await self._read(fail=True)
        self.assertEqual(result, {"status": "failed", "neighbors": []})

    async def test_port_16_is_preserved(self):
        result = await self._read(neighbor=True)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["neighbors"][0]["local_port_number"], "16")
        self.assertEqual(result["neighbors"][0]["local_port_id"], "gigabitEthernet 1/0/16")


if __name__ == "__main__":
    unittest.main()
