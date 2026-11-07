"""Basic LLDP reader contract tests without requiring a network device."""
from __future__ import annotations

import ast
from pathlib import Path
import unittest


PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components/fritzbox_network_insight/discovery/lldp.py"
)


class TestLldpReader(unittest.TestCase):
    def test_module_parses(self) -> None:
        ast.parse(PATH.read_text(encoding="utf-8"))

    def test_read_only_and_bounded(self) -> None:
        source = PATH.read_text(encoding="utf-8")
        self.assertIn("walk_cmd", source)
        self.assertIn("MAX_ROWS = 64", source)
        self.assertIn("MAX_NEIGHBORS = 16", source)
        self.assertNotIn("set_cmd", source)


if __name__ == "__main__":
    unittest.main()
