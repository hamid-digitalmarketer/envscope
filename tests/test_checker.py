"""Tests for envscope.checker."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from envscope.checker import check, mask_value  # noqa: E402
from envscope.parser import parse_env  # noqa: E402
from envscope.schema import Spec  # noqa: E402

EXAMPLE = """
APP_NAME=envscope
DEBUG=false
PORT=8080
API_TOKEN=replace-me
REDIS_URL=redis://localhost:6379
"""

SCHEMA = {
    "APP_NAME": Spec(type="string"),
    "DEBUG": Spec(type="bool"),
    "PORT": Spec(type="port"),
    "API_TOKEN": Spec(type="string", secret=True),
    "REDIS_URL": Spec(type="url", required=False),
    "LOG_LEVEL": Spec(type="string", choices=["info", "debug"], required=False),
}


def run(env_text: str, strict: bool = False):
    return check(parse_env(EXAMPLE), parse_env(env_text), SCHEMA, strict=strict)


class CheckerTests(unittest.TestCase):
    def test_clean_env(self) -> None:
        report = run(
            "APP_NAME=envscope\nDEBUG=false\nPORT=8080\n"
            "API_TOKEN=abc\nREDIS_URL=redis://localhost:6379\nLOG_LEVEL=info\n"
        )
        self.assertTrue(report.ok)
        self.assertEqual(report.stats["errors"], 0)
        self.assertEqual(report.issues, [])

    def test_missing_required_is_error_and_optional_is_warning(self) -> None:
        report = run("APP_NAME=envscope\nDEBUG=false\nPORT=8080\n")
        codes = {(issue.key, issue.code) for issue in report.issues}
        self.assertIn(("API_TOKEN", "missing"), codes)
        self.assertIn(("REDIS_URL", "missing"), codes)
        self.assertFalse(report.ok)
        levels = {issue.key: issue.level for issue in report.issues}
        self.assertEqual(levels["API_TOKEN"], "error")
        self.assertEqual(levels["REDIS_URL"], "warning")

    def test_empty_required_value_is_error(self) -> None:
        report = run("APP_NAME=\nDEBUG=false\nPORT=8080\nAPI_TOKEN=x\n")
        self.assertIn(("APP_NAME", "empty"), {(i.key, i.code) for i in report.issues})

    def test_extra_key_is_warning_but_strict_makes_it_error(self) -> None:
        text = "APP_NAME=envscope\nDEBUG=false\nPORT=8080\nAPI_TOKEN=x\nEXTRA=1\n"
        warning = run(text)
        self.assertIn("extra", [issue.code for issue in warning.warnings])
        strict = run(text, strict=True)
        self.assertFalse(strict.ok)
        self.assertEqual(strict.errors[-1].code, "extra")

    def test_invalid_values(self) -> None:
        report = run("APP_NAME=envscope\nDEBUG=maybe\nPORT=70000\nAPI_TOKEN=x\n")
        messages = " ".join(issue.message for issue in report.issues)
        self.assertIn("must be true/false", messages)
        self.assertIn("between 1 and 65535", messages)

    def test_duplicate_key_is_error(self) -> None:
        report = run("APP_NAME=a\nAPP_NAME=b\nDEBUG=false\nPORT=8080\nAPI_TOKEN=x\n")
        self.assertIn("duplicate", [issue.code for issue in report.issues])

    def test_mask_value(self) -> None:
        self.assertEqual(mask_value("super-secret"), "***")
        self.assertEqual(mask_value(""), "")


if __name__ == "__main__":
    unittest.main()
