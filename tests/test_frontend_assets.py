"""Guard against incomplete frontend packages."""
from pathlib import Path
import unittest


WWW = Path(__file__).resolve().parents[1] / "custom_components" / "fritzbox_network_insight" / "www"


class TestFrontendAssets(unittest.TestCase):
    def test_frontend_assets_are_present(self):
        required = (
            "fritz-network-insight-map-card.js",
            "fritz-network-insight-topology-dialog.js",
            "translations/de.js",
            "translations/en.js",
        )
        missing = [name for name in required if not (WWW / name).is_file() or not (WWW / name).stat().st_size]
        self.assertFalse(missing, f"Missing or empty frontend assets: {', '.join(missing)}")
