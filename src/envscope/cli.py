"""Command line interface for envscope."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

from . import __version__
from .checker import Issue, Report, check
from .parser import parse_env, read_env
from .schema import Spec, SchemaError, auto_secret, guess_type, load_schema

DEFAULT_ENV = ".env"
DEFAULT_EXAMPLE = ".env.example"
DEFAULT_SCHEMA = "envscope.json"

_COLORS = {
    "red": "\033[31m",
    "yellow": "\033[33m",
    "green": "\033[32m",
    "cyan": "\033[36m",
    "bold": "\033[1m",
    "reset": "\033[0m",
}
_LABELS = {"error": "ERROR", "warning": "WARN", "info": "INFO"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="envscope",
        description="Audit .env against .env.example and a schema, without printing secrets.",
    )
    parser.add_argument("--version", action="version", version=f"envscope {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    check_parser = sub.add_parser("check", help="compare .env with the example and schema")
    check_parser.add_argument("--env", default=DEFAULT_ENV, help="dotenv file to check")
    check_parser.add_argument("--example", default=DEFAULT_EXAMPLE, help="reference dotenv file")
    check_parser.add_argument(
        "--schema",
        default=None,
        help=f"JSON schema file (default: {DEFAULT_SCHEMA} when it exists)",
    )
    check_parser.add_argument("--strict", action="store_true", help="treat warnings as errors")
    check_parser.add_argument("--json", action="store_true", help="machine-readable output")
    check_parser.add_argument("--quiet", action="store_true", help="print only the summary")
    check_parser.add_argument("--no-color", action="store_true", help="disable ANSI colours")
    check_parser.set_defaults(func=cmd_check)

    init_parser = sub.add_parser("init", help="generate a schema from .env.example")
    init_parser.add_argument("--example", default=DEFAULT_EXAMPLE, help="reference dotenv file")
    init_parser.add_argument("--out", default=DEFAULT_SCHEMA, help="schema file to write")
    init_parser.add_argument("--force", action="store_true", help="overwrite an existing schema")
    init_parser.set_defaults(func=cmd_init)

    version_parser = sub.add_parser("version", help="print the version")
    version_parser.set_defaults(func=cmd_version)
    return parser


def _color(text: str, name: str, enabled: bool) -> str:
    if not enabled:
        return text
    return f"{_COLORS[name]}{text}{_COLORS['reset']}"


def _print_report(report: Report, env_path: str, example_path: str,
                  schema_path: Optional[str], no_color: bool, quiet: bool) -> None:
    color = sys.stdout.isatty() and not no_color
    header = (
        f"envscope {__version__} | env={env_path} | example={example_path}"
        + (f" | schema={schema_path}" if schema_path else "")
    )
    if not quiet:
        print(header)
        print("-" * min(len(header), 78))
        for issue in report.issues:
            label = _LABELS.get(issue.level, "INFO")
            if issue.level == "error":
                label = _color(label, "red", color)
            elif issue.level == "warning":
                label = _color(label, "yellow", color)
            else:
                label = _color(label, "cyan", color)
            location = f" (line {issue.line})" if issue.line else ""
            print(f"{label:17} {issue.message}{location}")
        if report.issues:
            print("-" * min(len(header), 78))

    stats = report.stats
    summary = (
        f"{stats.get('present', 0)}/{stats.get('expected', 0)} keys present | "
        f"{stats.get('errors', 0)} errors | {stats.get('warnings', 0)} warnings"
    )
    if report.ok:
        print(_color(f"OK   {summary}", "green", color))
    else:
        print(_color(f"FAIL {summary}", "red", color))


def _json_report(report: Report) -> str:
    payload = {
        "tool": "envscope",
        "version": __version__,
        "ok": report.ok,
        "summary": report.stats,
        "issues": [issue.to_dict() for issue in report.issues],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def cmd_check(args: argparse.Namespace) -> int:
    env_path = Path(args.env)
    example_path = Path(args.example)
    if not env_path.exists():
        print(f"envscope: error: env file not found: {env_path}", file=sys.stderr)
        return 2
    if not example_path.exists():
        print(f"envscope: error: example file not found: {example_path}", file=sys.stderr)
        return 2

    schema_path = args.schema
    if schema_path is None and Path(DEFAULT_SCHEMA).exists():
        schema_path = DEFAULT_SCHEMA

    schema: Dict[str, Spec] = {}
    if schema_path:
        schema = load_schema(Path(schema_path))

    example = read_env(example_path)
    env = read_env(env_path)
    report = check(example, env, schema, strict=args.strict)

    if args.json:
        print(_json_report(report))
    else:
        _print_report(report, str(env_path), str(example_path), schema_path,
                      args.no_color, args.quiet)
    return 0 if report.ok else 1


def cmd_init(args: argparse.Namespace) -> int:
    example_path = Path(args.example)
    out_path = Path(args.out)
    if not example_path.exists():
        print(f"envscope: error: example file not found: {example_path}", file=sys.stderr)
        return 2
    if out_path.exists() and not args.force:
        print(f"envscope: error: {out_path} already exists (use --force)", file=sys.stderr)
        return 1

    parsed = read_env(example_path)
    variables: Dict[str, Dict[str, object]] = {}
    for entry in parsed.entries:
        if entry.key in variables:
            continue
        variables[entry.key] = {
            "type": guess_type(entry.key, entry.value),
            "required": True,
            "secret": auto_secret(entry.key),
        }

    out_path.write_text(
        json.dumps({"variables": variables}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {out_path} ({len(variables)} variables)")
    return 0


def cmd_version(_args: argparse.Namespace) -> int:
    print(__version__)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except SchemaError as exc:
        print(f"envscope: error: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"envscope: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
