"""Unit tests for conservative, exact SNMP device identification."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "fritzbox_network_insight"
    / "snmp_device_classifier.py"
)
spec = importlib.util.spec_from_file_location("snmp_device_classifier", MODULE_PATH)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class TestSnmpDeviceClassifier(unittest.TestCase):
    def test_verified_switch_oid(self) -> None:
        actual = module.classify_snmp_system({
            "sys_object_id": "1.3.6.1.4.1.11863.5.364",
            "sys_descr": "Omada Access 24-Port Gigabit Switch with 4 SFP Slots",
            "sys_name": "SG3428",
        })
        self.assertEqual(actual["detected_device_type"], "switch")
        self.assertEqual(actual["device_model"], "SG3428")
        self.assertEqual(actual["device_type_confidence"], "high")

    def test_unknown_oid_is_not_guessed_from_description(self) -> None:
        self.assertEqual(
            module.classify_snmp_system({
                "sys_object_id": "1.3.6.1.4.1.99999.123",
                "sys_descr": "Switch with 24 ports",
                "sys_name": "SG3428",
            }),
            {},
        )

    def test_missing_oid_is_unknown(self) -> None:
        self.assertEqual(module.classify_snmp_system({"sys_name": "SG3428"}), {})


if __name__ == "__main__":
    unittest.main()
