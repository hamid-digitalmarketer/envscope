"""Drift detection between a dotenv file, its example and a schema."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .parser import ParseResult
from .schema import Spec, validate_value


@dataclass
class Issue:
    """A single finding produced by :func:`check`."""

    level: str  # "error" | "warning" | "info"
    code: str
    message: str
    key: Optional[str] = None
    line: Optional[int] = None

    def to_dict(self) -> Dict[str, object]:
        payload: Dict[str, object] = {
            "level": self.level,
            "code": self.code,
            "message": self.message,
        }
        if self.key is not None:
            payload["key"] = self.key
        if self.line is not None:
            payload["line"] = self.line
        return payload


@dataclass
class Report:
    """Result of a check run."""

    issues: List[Issue] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)

    @property
    def errors(self) -> List[Issue]:
        return [issue for issue in self.issues if issue.level == "error"]

    @property
    def warnings(self) -> List[Issue]:
        return [issue for issue in self.issues if issue.level == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> Dict[str, object]:
        return {
            "ok": self.ok,
            "summary": dict(self.stats),
            "issues": [issue.to_dict() for issue in self.issues],
        }


def mask_value(value: str) -> str:
    """Return a display-safe placeholder for a secret value."""
    if not value:
        return ""
    return "***"


def _line(result: ParseResult, key: str) -> Optional[int]:
    lines = result.lines_for(key)
    return lines[0] if lines else None


def check(
    example: ParseResult,
    env: ParseResult,
    schema: Dict[str, Spec],
    strict: bool = False,
) -> Report:
    """Compare *env* with *example* and *schema*.

    When ``strict`` is true, warnings are promoted to errors. This is useful
    in CI, where an unexpected key should fail the build.
    """
    report = Report()
    seen: Dict[str, bool] = {}

    def add(level: str, code: str, message: str, key: Optional[str] = None,
            line: Optional[int] = None) -> None:
        if strict and level == "warning":
            level = "error"
        report.issues.append(Issue(level=level, code=code, message=message,
                                   key=key, line=line))

    for message in example.errors:
        add("error", "parse", f".env.example: {message}")
    for message in env.errors:
        add("error", "parse", f".env: {message}")
    for key, lines in example.duplicates.items():
        add("error", "duplicate",
            f"key {key} appears {len(lines)} times in .env.example "
            f"(lines {', '.join(map(str, lines))})", key=key, line=lines[0])
    for key, lines in env.duplicates.items():
        add("error", "duplicate",
            f"key {key} appears {len(lines)} times in .env "
            f"(lines {', '.join(map(str, lines))})", key=key, line=lines[0])

    expected: List[str] = []
    for key in example.keys:
        if key not in seen:
            expected.append(key)
            seen[key] = True
    for key in schema:
        if key not in seen:
            expected.append(key)
            seen[key] = True

    env_values = env.as_dict()
    for key in expected:
        spec = schema.get(key, Spec(required=True))
        if key not in env_values:
            add("error" if spec.required else "warning", "missing",
                f"missing key {key}", key=key)
            continue
        value = env_values[key]
        line = _line(env, key)
        if value == "":
            add("error" if spec.required else "warning", "empty",
                f"key {key} has an empty value", key=key, line=line)
            continue
        problem = validate_value(spec, value)
        if problem:
            add("error", "invalid", f"key {key}: {problem}", key=key, line=line)

    for key in env.keys:
        if key in seen:
            continue
        add("warning", "extra",
            f"key {key} is set in .env but not in .env.example or schema",
            key=key, line=_line(env, key))

    present = sum(1 for key in expected if key in env_values)
    report.stats = {
        "expected": len(expected),
        "present": present,
        "missing": len(expected) - present,
        "extra": sum(1 for key in env.keys if key not in seen),
        "errors": len(report.errors),
        "warnings": len(report.warnings),
    }
    return report
