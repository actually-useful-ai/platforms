# File Purpose: Verify canonical skill and agent inventory matches suite.toml.
# Primary Functions/Classes: InventoryPresenceTests.
# Inputs/Outputs: Reads suite.toml and skills/agents trees; asserts SKILL.md presence.

from __future__ import annotations

import unittest
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


ROOT = Path(__file__).resolve().parents[1]


class InventoryPresenceTests(unittest.TestCase):
    def test_every_suite_skill_has_skill_md(self) -> None:
        suite = tomllib.loads((ROOT / "suite.toml").read_text(encoding="utf-8"))
        for skill in suite["skills"]:
            path = ROOT / "skills" / skill["id"] / "SKILL.md"
            self.assertTrue(path.is_file(), f"missing {path}")
            text = path.read_text(encoding="utf-8")
            self.assertIn("name:", text)
            self.assertNotIn("AI-powered", text)
            self.assertNotIn("AI-driven", text)

    def test_every_suite_agent_has_definition(self) -> None:
        suite = tomllib.loads((ROOT / "suite.toml").read_text(encoding="utf-8"))
        for agent in suite["agents"]:
            path = ROOT / "agents" / f"{agent['id']}.md"
            self.assertTrue(path.is_file(), f"missing {path}")
            self.assertIn("read-only", path.read_text(encoding="utf-8").lower())
