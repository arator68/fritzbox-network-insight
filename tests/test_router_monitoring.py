"""Tests for optional router metrics without a Home Assistant runtime."""
import ast
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "custom_components" / "fritzbox_network_insight" / "router_monitoring.py"
TREE = ast.parse(SOURCE.read_text(encoding="utf-8"))
NODES = [node for node in TREE.body if isinstance(node, (ast.FunctionDef, ast.Assign))]
SCOPE = {"Any": Any, "ip_address": __import__("ipaddress").ip_address}
exec(compile(ast.Module(body=NODES, type_ignores=[]), str(SOURCE), "exec"), SCOPE)
read_router_metrics = SCOPE["read_router_metrics"]


class FakeConnection:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def call_action(self, service, action):
        self.calls.append((service, action))
        response = self.responses.get((service, action))
        if isinstance(response, Exception):
            raise response
        if response is None:
            raise RuntimeError("unsupported")
        return response


class RouterMonitoringTests(unittest.TestCase):
    def test_unsupported_actions_create_no_values(self):
        self.assertEqual(read_router_metrics(FakeConnection({})), {})

    def test_valid_zero_and_positive_values(self):
        connection = FakeConnection({
            ("WANCommonInterfaceConfig", "GetAddonInfos"): {
                "NewByteReceiveRate": "0", "NewByteSendRate": "1234",
            },
            ("WANCommonInterfaceConfig", "GetTotalBytesReceived"): {
                "NewTotalBytesReceived": "98765",
            },
            ("WANIPConnection", "GetExternalIPAddress"): {
                "NewExternalIPAddress": "203.0.113.5",
            },
        })
        values = read_router_metrics(connection)
        self.assertEqual(values["download_rate"], 0)
        self.assertEqual(values["upload_rate"], 1234)
        self.assertEqual(values["bytes_received"], 98765)
        self.assertEqual(values["external_ipv4"], "203.0.113.5")
        self.assertNotIn("bytes_sent", values)
        self.assertEqual(connection.calls.count(("WANCommonInterfaceConfig", "GetAddonInfos")), 1)

    def test_invalid_values_not_published(self):
        connection = FakeConnection({
            ("WANCommonInterfaceConfig", "GetAddonInfos"): {
                "NewByteReceiveRate": "-1", "NewByteSendRate": "unknown",
            },
            ("WANIPConnection", "GetExternalIPAddress"): {
                "NewExternalIPAddress": "0.0.0.0",
            },
            ("DeviceInfo", "GetInfo"): {"NewSoftwareVersion": ""},
        })
        self.assertEqual(read_router_metrics(connection), {})

    def test_ppp_fallback(self):
        connection = FakeConnection({
            ("WANPPPConnection", "GetExternalIPAddress"): {
                "NewExternalIPAddress": "198.51.100.8",
            },
            ("WANPPPConnection", "GetStatusInfo"): {"NewUptime": 0},
        })
        values = read_router_metrics(connection)
        self.assertEqual(values["external_ipv4"], "198.51.100.8")
        self.assertEqual(values["uptime"], 0)


if __name__ == "__main__":
    unittest.main()
