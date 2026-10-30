"""Tests for envscope.parser."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from envscope.parser import is_valid_key, parse_env, parse_value  # noqa: E402


class ParseValueTests(unittest.TestCase):
    def test_unquoted_value_and_inline_comment(self) -> None:
        self.assertEqual(parse_value("hello world # comment"), ("hello world", None))

    def test_double_quotes_keep_hash_and_unescape(self) -> None:
        self.assertEqual(parse_value('"hello # world\\nnext"'), ("hello # world\nnext", '"'))

    def test_single_quotes_are_literal(self) -> None:
        self.assertEqual(parse_value("'a\\nb'"), ("a\\nb", "'"))

    def test_empty_value(self) -> None:
        self.assertEqual(parse_value("   "), ("", None))


class ParseEnvTests(unittest.TestCase):
    def test_name(self) -> None:
        text = """
# comment
APP_NAME=envscope
export DEBUG=false
URL="https://example.com/a#fragment"
NOTE='literal $VALUE'
PORT=8080 # inline comment
"""
        result = parse_env(text)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.as_dict(), {
            "APP_NAME": "envscope",
            "DEBUG": "false",
            "URL": "https://example.com/a#fragment",
            "NOTE": "literal $VALUE",
            "PORT": "8080",
        })
        self.assertEqual(result.duplicates, {})
        self.assertTrue(result.entries[1].exported)

    def test_duplicates_are_reported(self) -> None:
        result = parse_env("A=1\nB=2\nA=3\n")
        self.assertEqual(result.duplicates, {"A": [1, 3]})
        self.assertEqual(result.as_dict()["A"], "3")

    def test_invalid_lines_are_errors(self) -> None:
        result = parse_env("GOOD=1\nnot a line\n1BAD=2\n")
        self.assertEqual(len(result.errors), 2)
        self.assertEqual(result.keys, ["GOOD"])

    def test_blank_and_comment_only(self) -> None:
        result = parse_env("\n# only comments\n   \n")
        self.assertEqual(result.entries, [])
        self.assertEqual(result.errors, [])

    def test_is_valid_key(self) -> None:
        self.assertTrue(is_valid_key("APP_URL"))
        self.assertTrue(is_valid_key("_private"))
        self.assertFalse(is_valid_key("1APP"))
        self.assertFalse(is_valid_key("APP-URL"))


if __name__ == "__main__":
    unittest.main()
