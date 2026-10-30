"""Tests for envscope.schema."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from envscope.schema import (  # noqa: E402
    SchemaError,
    Spec,
    auto_secret,
    guess_type,
    load_schema,
    validate_value,
)


class LoadSchemaTests(unittest.TestCase):
    def _write(self, payload: object) -> Path:
        handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        with handle:
            json.dump(payload, handle)
        self.addCleanup(lambda: Path(handle.name).unlink(missing_ok=True))
        return Path(handle.name)

    def test_flat_and_nested_shapes(self) -> None:
        flat = load_schema(self._write({"PORT": "port"}))
        nested = load_schema(self._write({"variables": {"PORT": {"type": "port"}}}))
        self.assertEqual(flat["PORT"].type, "port")
        self.assertEqual(nested["PORT"].type, "port")

    def test_invalid_type(self) -> None:
        with self.assertRaises(SchemaError):
            load_schema(self._write({"PORT": "integer"}))

    def test_invalid_json(self) -> None:
        path = Path(tempfile.mkstemp(suffix=".json")[1])
        path.write_text("{not json", encoding="utf-8")
        self.addCleanup(path.unlink, missing_ok=True)
        with self.assertRaises(SchemaError):
            load_schema(path)

    def test_pattern_must_compile(self) -> None:
        with self.assertRaises(SchemaError):
            load_schema(self._write({"A": {"pattern": "["}}))


class GuessTypeTests(unittest.TestCase):
    def test_examples(self) -> None:
        self.assertEqual(guess_type("PORT", "8080"), "port")
        self.assertEqual(guess_type("DATABASE_URL", "postgres://x"), "url")
        self.assertEqual(guess_type("SMTP_FROM", "a@b.it"), "email")
        self.assertEqual(guess_type("DEBUG", "false"), "bool")
        self.assertEqual(guess_type("RETRY_COUNT", "3"), "int")
        self.assertEqual(guess_type("RATIO", "1.5"), "float")
        self.assertEqual(guess_type("NAME", "envscope"), "string")


class ValidateTests(unittest.TestCase):
    def test_int(self) -> None:
        self.assertIsNone(validate_value(Spec(type="int"), "42"))
        self.assertIsNotNone(validate_value(Spec(type="int"), "4.2"))

    def test_port(self) -> None:
        self.assertIsNone(validate_value(Spec(type="port"), "8080"))
        self.assertIsNotNone(validate_value(Spec(type="port"), "0"))
        self.assertIsNotNone(validate_value(Spec(type="port"), "70000"))

    def test_bool(self) -> None:
        for value in ["true", "FALSE", "1", "0", "yes", "off"]:
            self.assertIsNone(validate_value(Spec(type="bool"), value), value)
        self.assertIsNotNone(validate_value(Spec(type="bool"), "maybe"))

    def test_url_and_email(self) -> None:
        self.assertIsNone(validate_value(Spec(type="url"), "https://example.com/x"))
        self.assertIsNotNone(validate_value(Spec(type="url"), "example.com"))
        self.assertIsNone(validate_value(Spec(type="email"), "a@b.it"))
        self.assertIsNotNone(validate_value(Spec(type="email"), "not-an-email"))

    def test_choices_and_pattern(self) -> None:
        spec = Spec(type="string", choices=["info", "debug"])
        self.assertIsNone(validate_value(spec, "info"))
        self.assertIsNotNone(validate_value(spec, "verbose"))
        pattern = Spec(type="string", pattern=r"[a-z]+")
        self.assertIsNone(validate_value(pattern, "abc"))
        self.assertIsNotNone(validate_value(pattern, "ABC"))

    def test_secret_detection(self) -> None:
        self.assertTrue(auto_secret("API_TOKEN"))
        self.assertTrue(auto_secret("DB_PASSWORD"))
        self.assertFalse(auto_secret("APP_NAME"))
        self.assertTrue(Spec().is_secret("MY_SECRET"))


if __name__ == "__main__":
    unittest.main()
