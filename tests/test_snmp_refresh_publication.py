"""Regression guard: automatic SNMP refresh must not publish partial state."""
import ast
from pathlib import Path
import unittest


SOURCE = (
    Path(__file__).resolve().parents[1]
    / "custom_components/fritzbox_network_insight/coordinator.py"
)


class SnmpRefreshPublicationTests(unittest.TestCase):
    def test_automatic_scan_defers_sensor_publication(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        coordinator = next(
            node for node in tree.body
            if isinstance(node, ast.ClassDef)
            and node.name == "FritzBoxDataUpdateCoordinator"
        )
        refresh = next(
            node for node in coordinator.body
            if isinstance(node, ast.AsyncFunctionDef)
            and node.name == "_async_refresh_snmp_topology"
        )
        calls = [
            node for node in ast.walk(refresh)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "async_record_manual_discovery"
        ]
        self.assertEqual(len(calls), 1)
        options = {kw.arg: kw.value for kw in calls[0].keywords}
        self.assertIn("publish", options)
        self.assertIsInstance(options["publish"], ast.Constant)
        self.assertIs(options["publish"].value, False)

    def test_manual_discovery_still_publishes(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        coordinator = next(
            node for node in tree.body
            if isinstance(node, ast.ClassDef)
            and node.name == "FritzBoxDataUpdateCoordinator"
        )
        method = next(
            node for node in coordinator.body
            if isinstance(node, ast.AsyncFunctionDef)
            and node.name == "async_record_manual_discovery"
        )
        self.assertEqual(method.args.kw_defaults[-1].value, True)
        guarded = [
            node for node in ast.walk(method)
            if isinstance(node, ast.If)
            and isinstance(node.test, ast.Name)
            and node.test.id == "publish"
            and any(
                isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute)
                and call.func.attr == "async_update_listeners"
                for stmt in node.body for call in ast.walk(stmt)
            )
        ]
        self.assertEqual(len(guarded), 1)


if __name__ == "__main__":
    unittest.main()
