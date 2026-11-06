"""Basic tests for the integration package metadata."""

import json
from pathlib import Path
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = (
    REPOSITORY_ROOT
    / "custom_components"
    / "fritzbox_network_insight"
    / "manifest.json"
)


class TestManifest(unittest.TestCase):
    """Validate the Home Assistant integration manifest."""

    def test_manifest_is_valid_json(self) -> None:
        with MANIFEST_PATH.open(encoding="utf-8") as manifest_file:
            manifest = json.load(manifest_file)

        self.assertEqual(
            manifest["domain"],
            "fritzbox_network_insight",
        )
        self.assertEqual(
            manifest["name"],
            "FRITZ!Box Network Insight",
        )
        self.assertEqual(manifest["integration_type"], "hub")
        self.assertEqual(manifest["iot_class"], "local_polling")
        self.assertTrue(manifest["version"])


if __name__ == "__main__":
    unittest.main()
