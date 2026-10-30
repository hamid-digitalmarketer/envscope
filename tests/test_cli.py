"""End-to-end tests for the envscope CLI."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

EXAMPLE = """APP_NAME=envscope
DEBUG=false
PORT=8080
API_TOKEN=replace-me
REDIS_URL=redis://localhost:6379
"""

CLEAN = """APP_NAME=envscope
DEBUG=false
PORT=8080
API_TOKEN=local-token
REDIS_URL=redis://localhost:6379
"""

BROKEN = """APP_NAME=envscope
DEBUG=maybe
PORT=70000
API_TOKEN=local-token
EXTRA_FLAG=1
"""


class CliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        (self.dir / ".env.example").write_text(EXAMPLE, encoding="utf-8")
        schema = {
            "variables": {
                "APP_NAME": {"type": "string"},
                "DEBUG": {"type": "bool"},
                "PORT": {"type": "port"},
                "API_TOKEN": {"type": "string", "secret": True},
                "REDIS_URL": {"type": "url", "required": False},
            }
        }
        (self.dir / "envscope.json").write_text(json.dumps(schema), encoding="utf-8")

    def run_cli(self, *args: str) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        env["PYTHONPATH"] = str(SRC) + os.pathsep + env.get("PYTHONPATH", "")
        return subprocess.run(
            [sys.executable, "-m", "envscope", *args],
            cwd=self.dir,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_clean_check_exits_zero(self) -> None:
        (self.dir / ".env").write_text(CLEAN, encoding="utf-8")
        result = self.run_cli("check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("OK", result.stdout)

    def test_broken_check_json_and_exit_code(self) -> None:
        (self.dir / ".env").write_text(BROKEN, encoding="utf-8")
        result = self.run_cli("check", "--json")
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["ok"])
        self.assertGreater(payload["summary"]["errors"], 0)
        codes = {issue["code"] for issue in payload["issues"]}
        self.assertIn("invalid", codes)
        self.assertIn("extra", codes)
        self.assertIn("missing", codes)

    def test_strict_promotes_warnings(self) -> None:
        (self.dir / ".env").write_text(BROKEN, encoding="utf-8")
        lenient = self.run_cli("check")
        strict = self.run_cli("check", "--strict")
        self.assertEqual(lenient.returncode, 1)  # already has real errors
        self.assertIn("WARN", lenient.stdout)
        self.assertNotIn("WARN", strict.stdout)

    def test_clean_extra_only_in_lenient_is_warning(self) -> None:
        text = CLEAN + "EXTRA_FLAG=1\n"
        (self.dir / ".env").write_text(text, encoding="utf-8")
        lenient = self.run_cli("check", "--json")
        self.assertEqual(lenient.returncode, 0)
        payload = json.loads(lenient.stdout)
        self.assertEqual(payload["summary"]["warnings"], 1)
        strict = self.run_cli("check", "--strict")
        self.assertEqual(strict.returncode, 1)

    def test_init_generates_schema(self) -> None:
        (self.dir / "envscope.json").unlink()
        result = self.run_cli("init")
        self.assertEqual(result.returncode, 0, result.stderr)
        schema = json.loads((self.dir / "envscope.json").read_text(encoding="utf-8"))
        self.assertIn("PORT", schema["variables"])
        self.assertEqual(schema["variables"]["PORT"]["type"], "port")
        second = self.run_cli("init")
        self.assertEqual(second.returncode, 1)
        forced = self.run_cli("init", "--force")
        self.assertEqual(forced.returncode, 0)

    def test_missing_files_exit_two(self) -> None:
        result = self.run_cli("check", "--env", "missing.env")
        self.assertEqual(result.returncode, 2)
        self.assertIn("not found", result.stderr)

    def test_version(self) -> None:
        result = self.run_cli("version")
        self.assertEqual(result.returncode, 0)
        self.assertRegex(result.stdout.strip(), r"^\d+\.\d+\.\d+$")


if __name__ == "__main__":
    unittest.main()
