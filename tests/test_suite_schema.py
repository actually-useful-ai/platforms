# File Purpose: Validate suite.toml against the published JSON Schema.
# Primary Functions/Classes: SuiteSchemaTests.
# Inputs/Outputs: Reads TOML and JSON Schema documents; asserts standards-based validation.

from __future__ import annotations

import json
import tomllib
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]


class SuiteSchemaTests(unittest.TestCase):
    def test_suite_toml_validates_against_published_schema(self) -> None:
        schema = json.loads(
            (ROOT / "schemas/suite.schema.json").read_text(encoding="utf-8")
        )
        suite = tomllib.loads((ROOT / "suite.toml").read_text(encoding="utf-8"))

        Draft202012Validator.check_schema(schema)
        errors = sorted(
            Draft202012Validator(schema).iter_errors(suite),
            key=lambda error: list(error.absolute_path),
        )

        self.assertEqual([error.message for error in errors], [])
        self.assertIn("aliases", schema["properties"])
        self.assertIn("aliases", schema["required"])


if __name__ == "__main__":
    unittest.main()
