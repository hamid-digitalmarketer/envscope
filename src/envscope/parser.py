"""Dotenv parsing for envscope.

The parser intentionally implements the small, predictable subset of the
dotenv format that is useful for drift detection:

* blank lines and ``#`` comments are ignored;
* ``export KEY=value`` is accepted;
* single and double quoted values are supported, including ``\\n`` escapes
  inside double quotes;
* double-quoted values may span multiple lines; the newlines that separate
  them are preserved in the parsed value, and an unterminated value is
  reported as a parse error;
* single-quoted values are deliberately kept literal and single-line: no
  escapes are processed and a value never continues past its line, which
  keeps the subset predictable for secrets;
* inline comments (``KEY=value # comment``) are stripped for unquoted values;
* duplicate keys are reported, not silently overwritten.

It is not a full dotenv implementation: variable interpolation is out of
scope (see ``docs/roadmap.md``).
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
    quote; :func:`parse_env` is stricter and reports unterminated
    double-quoted values as parse errors.
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


def _dq_terminated(raw: str) -> bool:
    """True when the double-quoted value starting *raw* is closed."""
    index = 1
    escaped = False
    while index < len(raw):
        char = raw[index]
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == '"':
            return True
        index += 1
    return False


def _split_line_end(raw_line: str) -> tuple[str, str]:
    """Split a physical line into ``(content, ending)``."""
    if raw_line.endswith("\r\n"):
        return raw_line[:-2], "\r\n"
    if raw_line.endswith("\n"):
        return raw_line[:-1], "\n"
    return raw_line, ""


def _read_dq_multiline(pieces: List[str], endings: List[str]) -> tuple[str, bool]:
    """Read a double-quoted value spanning several physical lines.

    *pieces* holds the content of each consumed line, starting with the
    right-hand side of the line where the value began (opening quote
    included); *endings[i]* is the line ending that followed *pieces[i]*.
    Returns the unescaped content and whether a closing quote was found
    before the end of the input.
    """
    parts: List[str] = []
    chars: List[str] = []
    escaped = False

    def flush() -> None:
        if chars:
            parts.append("".join(chars))
            chars.clear()

    index = 1  # skip the opening quote on the first line
    for position, piece in enumerate(pieces):
        while index < len(piece):
            char = piece[index]
            if escaped:
                chars.append(_DQ_ESCAPES.get(char, char))
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                flush()
                return "".join(parts), True
            else:
                chars.append(char)
            index += 1
        flush()
        if endings[position]:
            parts.append(endings[position])
        index = 0
    flush()
    return "".join(parts), False


def parse_env(text: str, path: Optional[Path] = None) -> ParseResult:
    """Parse dotenv *text* into a :class:`ParseResult`."""
    result = ParseResult(path=path)
    positions: Dict[str, List[int]] = {}
    lines = re.split(r"(?<=\n)", text)
    total = len(lines)
    i = 0

    while i < total:
        number = i + 1
        raw_line = lines[i]
        line = raw_line.strip()
        i += 1
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
        if quote == '"' and not _dq_terminated(raw_value):
            pieces = [raw_value]
            endings = [_split_line_end(raw_line)[1]]
            while i < total:
                content, ending = _split_line_end(lines[i])
                i += 1
                pieces.append(content)
                endings.append(ending)
                if _dq_terminated(content):
                    break
            value, closed = _read_dq_multiline(pieces, endings)
            if not closed:
                result.errors.append(
                    f"line {number}: unterminated double-quoted value"
                )
                continue

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
