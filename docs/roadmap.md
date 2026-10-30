# Roadmap

Three small, self-contained tasks. Each one is a good candidate for an AI-assisted coding session: the scope is clear, the tests are fast, and the acceptance criteria are testable.

---

## 1. Support multiline quoted values

**Labels:** `enhancement`, `good first issue`

Today the parser reads one line at a time, so this is not supported:

```dotenv
PRIVATE_KEY="-----BEGIN KEY-----
abc
-----END KEY-----"
```

### Acceptance criteria

- Double-quoted values may span multiple lines; newlines are preserved.
- A closing quote on a later line ends the value.
- Unterminated multiline values produce a `parse` error with the starting line.
- Single-quoted values keep the current literal behaviour; document the choice.
- Tests cover: two-line value, escaped `\"` inside, unterminated value, CRLF input.

### Hints

- `parse_env` currently iterates `text.splitlines()`. Consider a small state machine that consumes lines while a quote is open.
- Keep the existing `Entry.line` pointing at the first line of the value.

---

## 2. Add `--fix` to append missing keys

**Labels:** `enhancement`

Typing missing variables by hand is the most common follow-up to a failed check.

### Acceptance criteria

- `envscope check --fix` appends missing **required** keys to `.env` with an empty value and a comment.
- It never overwrites existing keys and never touches secret values.
- `--dry-run` prints the lines that would be appended without writing.
- The command exits `1` if errors remain after the fix (e.g. invalid types), `0` if the file is now complete.
- Tests cover: append, idempotency, `--dry-run`, read-only file error.

### Hints

- Reuse `Report.issues` filtered by `code == "missing"` and `level == "error"`.
- Write atomically: temporary file in the same directory, then `os.replace`.

---

## 3. Ship a pre-commit hook and a reusable GitHub Action

**Labels:** `enhancement`, `help wanted`

Make the tool one line away from being used in real repositories.

### Acceptance criteria

- `.pre-commit-hooks.yaml` exposes `envscope-check` with `--strict`.
- `action.yml` is a composite action with inputs `env`, `example`, `schema`, `strict`.
- A short section in the README shows both usages.
- CI runs the composite action against `examples/` and asserts the expected failure.

### Hints

- The action can install with `python -m pip install -e .` and run `envscope check`.
- The example in this repository is intentionally invalid: use `--json` and assert exit code `1` rather than expecting success.
