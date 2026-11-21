"""Independently validate the shared C0 examples with Python's JSON Schema validator."""

import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource


CONTRACTS = Path(__file__).resolve().parents[2] / "contracts"


class C0ContractTest(unittest.TestCase):
    def test_shared_cases(self):
        schemas = {
            path.name.removesuffix(".schema.json"): json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(CONTRACTS.glob("*.schema.json"))
        }
        for schema in schemas.values():
            Draft202012Validator.check_schema(schema)
        registry = Registry().with_resources(
            (schema["$id"], Resource.from_contents(schema)) for schema in schemas.values()
        )
        validators = {
            name: Draft202012Validator(schema, registry=registry, format_checker=FormatChecker())
            for name, schema in schemas.items()
        }
        cases = json.loads((CONTRACTS / "fixtures/cases.json").read_text(encoding="utf-8"))
        self.assertTrue(cases, "No shared fixture cases found")
        for index, case in enumerate(cases, start=1):
            with self.subTest(case=index, schema=case["schema"], valid=case["valid"]):
                errors = list(validators[case["schema"]].iter_errors(case["data"]))
                self.assertEqual(not errors, case["valid"], [error.message for error in errors])


if __name__ == "__main__":
    unittest.main()
