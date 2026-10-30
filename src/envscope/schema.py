"""Schema loading and type validation for envscope."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlsplit

VALID_TYPES = {"string", "int", "float", "bool", "url", "email", "port"}
_BOOL_VALUES = {"1", "0", "true", "false", "yes", "no", "on", "off"}
_SECRET_RE = re.compile(
    r"(SECRET|TOKEN|PASSWORD|PASSWD|API_KEY|PRIVATE_KEY|CREDENTIAL|DSN)", re.IGNORECASE
)
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_INT_RE = re.compile(r"^[+-]?\d+$")
_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class SchemaError(ValueError):
    """Raised when a schema file is missing or malformed."""


@dataclass
class Spec:
    """Validation rules for a single variable."""

    type: str = "string"
    required: bool = True
    pattern: Optional[str] = None
    choices: Optional[List[str]] = None
    secret: bool = False
    description: str = ""

    def is_secret(self, key: str) -> bool:
        return self.secret or bool(_SECRET_RE.search(key))


def load_schema(path: Path) -> Dict[str, Spec]:
    """Load a JSON schema from *path*.

    Accepted shape::

        {"variables": {"PORT": {"type": "port", "required": true}}}

    A flat ``{"PORT": "port"}`` mapping is also accepted for brevity.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise SchemaError(f"schema not found: {path}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SchemaError(f"invalid JSON in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise SchemaError(f"schema must be a JSON object: {path}")

    variables = data.get("variables", data)
    if not isinstance(variables, dict):
        raise SchemaError("'variables' must be a JSON object")

    specs: Dict[str, Spec] = {}
    for key, value in variables.items():
        if not _KEY_RE.match(key):
            raise SchemaError(f"invalid variable name in schema: {key!r}")
        specs[key] = _parse_spec(key, value)
    return specs


def _parse_spec(key: str, value: Any) -> Spec:
    if isinstance(value, str):
        value = {"type": value}
    if not isinstance(value, dict):
        raise SchemaError(f"rules for {key} must be an object or a type string")

    kind = value.get("type", "string")
    if kind not in VALID_TYPES:
        raise SchemaError(
            f"{key}: unknown type {kind!r} (expected one of {sorted(VALID_TYPES)})"
        )

    required = value.get("required", True)
    if not isinstance(required, bool):
        raise SchemaError(f"{key}: 'required' must be true or false")

    secret = value.get("secret", False)
    if not isinstance(secret, bool):
        raise SchemaError(f"{key}: 'secret' must be true or false")

    pattern = value.get("pattern")
    if pattern is not None:
        if not isinstance(pattern, str):
            raise SchemaError(f"{key}: 'pattern' must be a string")
        try:
            re.compile(pattern)
        except re.error as exc:
            raise SchemaError(f"{key}: invalid pattern: {exc}") from exc

    choices = value.get("choices")
    if choices is not None:
        if not isinstance(choices, list) or not all(
            isinstance(item, str) for item in choices
        ):
            raise SchemaError(f"{key}: 'choices' must be a list of strings")

    description = value.get("description", "")
    if not isinstance(description, str):
        raise SchemaError(f"{key}: 'description' must be a string")

    return Spec(
        type=kind,
        required=required,
        pattern=pattern,
        choices=choices,
        secret=secret,
        description=description,
    )


def guess_type(key: str, value: str) -> str:
    """Guess a schema type from a variable name and example value."""
    upper = key.upper()
    lowered = value.strip().lower()

    if upper.endswith("_URL") or upper in {"URL", "BASE_URL", "DATABASE_URL"}:
        return "url"
    if "EMAIL" in upper or "MAIL" in upper or _EMAIL_RE.match(value.strip()):
        return "email"
    if "PORT" in upper:
        return "port"
    if upper in {"DEBUG", "CI", "VERBOSE", "ENABLED", "ENABLE", "DRY_RUN"}:
        return "bool"
    if lowered in _BOOL_VALUES and (
        "ENABLE" in upper or upper.endswith("_FLAG") or upper in {"DEBUG", "CI"}
    ):
        return "bool"
    if any(
        token in upper
        for token in ("COUNT", "TIMEOUT", "RETRIES", "MAX", "MIN", "SIZE", "NUM")
    ):
        return "int"
    if _INT_RE.match(lowered):
        return "int"
    try:
        float(lowered)
    except ValueError:
        pass
    else:
        return "float"
    return "string"


def auto_secret(key: str) -> bool:
    return bool(_SECRET_RE.search(key))


def validate_value(spec: Spec, value: str) -> Optional[str]:
    """Return an error message when *value* does not satisfy *spec*."""
    if spec.choices is not None and value not in spec.choices:
        joined = ", ".join(repr(choice) for choice in spec.choices)
        return f"must be one of {joined}"

    if spec.pattern is not None and not re.fullmatch(spec.pattern, value):
        return f"does not match pattern {spec.pattern!r}"

    if spec.type == "string":
        return None
    if spec.type == "int":
        if not _INT_RE.match(value):
            return "must be an integer"
        return None
    if spec.type == "float":
        try:
            float(value)
        except ValueError:
            return "must be a number"
        return None
    if spec.type == "bool":
        if value.lower() not in _BOOL_VALUES:
            return "must be true/false (or 1/0, yes/no, on/off)"
        return None
    if spec.type == "port":
        if not _INT_RE.match(value):
            return "must be a TCP port number"
        port = int(value)
        if not 1 <= port <= 65535:
            return "must be between 1 and 65535"
        return None
    if spec.type == "url":
        parsed = urlsplit(value)
        if not parsed.scheme or not parsed.netloc:
            return "must be an absolute URL with a scheme and a host"
        if not re.match(r"^[A-Za-z][A-Za-z0-9+.-]*$", parsed.scheme):
            return "must use a valid URL scheme"
        return None
    if spec.type == "email":
        if not _EMAIL_RE.match(value):
            return "must be a valid email address"
        return None
    return None
