"""Dotenv parsing for envscope.

The parser intentionally implements the small, predictable subset of the
dotenv format that is useful for drift detection:

* blank lines and ``#`` comments are ignored;
* ``export KEY=value`` is accepted;
* single and double quoted values are supported, including ``\\n`` escapes
  inside double quotes;
* inline comments (``KEY=value # comment``) are stripped for unquoted values;
* duplicate keys are reported, not silently overwritten.

It is not a full dotenv implementation: variable interpolation and multiline
values are out of scope (see ``docs/roadmap.md``).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

_KEY_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_EXPORT_RE = re.compile(r"^export\s+", re.IGNORECASE)
_INLINE_COMMENT_RE = re.compile(r"\s+#")
_DQ_ESCAPES = {
    "n": "\n",
    "r": "\r",
    "t": "\t",
    '"': '"',
    "\\": "\\",
    "$": "$",
}


def is_valid_key(key: str) -> bool:
    """Return True when *key* is a conventional dotenv variable name."""
    return bool(_KEY_RE.match(key))


@dataclass
class Entry:
    """One parsed ``KEY=value`` line."""

    key: str
    value: str
    line: int
    exported: bool = False
    quoted: Optional[str] = None  # '"' or "'" when the value was quoted


@dataclass
class ParseResult:
    """Everything envscope knows about a single dotenv file."""

    path: Optional[Path] = None
    entries: List[Entry] = field(default_factory=list)
    duplicates: Dict[str, List[int]] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    @property
    def keys(self) -> List[str]:
        return [entry.key for entry in self.entries]

    def as_dict(self) -> Dict[str, str]:
        # Last assignment wins, mirroring dotenv loaders.
        return {entry.key: entry.value for entry in self.entries}

    def lines_for(self, key: str) -> List[int]:
        return [entry.line for entry in self.entries if entry.key == key]


def _read_quoted(raw: str, quote: str) -> str:
    """Read a quoted value, returning the unescaped content.

    An unterminated quote is treated as a literal value without the opening
    quote. The caller records no error for it: dotenv files in the wild
    contain this often enough that failing hard would be unhelpful.
    """
    chars: List[str] = []
    index = 1
    escaped = False
    while index < len(raw):
        char = raw[index]
        if escaped:
            if quote == '"':
                chars.append(_DQ_ESCAPES.get(char, char))
            else:
                chars.append(char)
            escaped = False
        elif char == "\\" and quote == '"':
            escaped = True
        elif char == quote:
            return "".join(chars)
        else:
            chars.append(char)
        index += 1
    return raw[1:]


def parse_value(raw: str) -> tuple[str, Optional[str]]:
    """Split a raw right-hand side into ``(value, quote)``."""
    stripped = raw.strip()
    if not stripped:
        return "", None
    if stripped[0] == '"':
        return _read_quoted(stripped, '"'), '"'
    if stripped[0] == "'":
        return _read_quoted(stripped, "'"), "'"

    comment = _INLINE_COMMENT_RE.search(stripped)
    if comment:
        stripped = stripped[: comment.start()].rstrip()
    return stripped, None


def parse_env(text: str, path: Optional[Path] = None) -> ParseResult:
    """Parse dotenv *text* into a :class:`ParseResult`."""
    result = ParseResult(path=path)
    positions: Dict[str, List[int]] = {}

    for number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        exported = False
        if _EXPORT_RE.match(line):
            exported = True
            line = _EXPORT_RE.sub("", line, count=1).strip()

        if "=" not in line:
            result.errors.append(
                f"line {number}: expected KEY=value, found {line!r}"
            )
            continue

        key, raw_value = line.split("=", 1)
        key = key.strip()
        if not is_valid_key(key):
            result.errors.append(
                f"line {number}: invalid variable name {key!r}"
            )
            continue

        value, quote = parse_value(raw_value)
        result.entries.append(
            Entry(key=key, value=value, line=number, exported=exported, quoted=quote)
        )
        positions.setdefault(key, []).append(number)

    result.duplicates = {
        key: lines for key, lines in positions.items() if len(lines) > 1
    }
    return result


def read_env(path: Path) -> ParseResult:
    """Read and parse a dotenv file from disk."""
    return parse_env(path.read_text(encoding="utf-8"), path=path)
