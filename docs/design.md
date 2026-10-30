# Design notes

`envscope` is small on purpose. These are the decisions that keep it small and predictable.

## Scope

The tool answers one question: *does this `.env` satisfy the contract described by `.env.example` and the schema?*

It does not load environment variables into a process, interpolate values, or talk to secret managers. Those are runtime concerns; mixing them in would make the output non-deterministic and the tool harder to test.

## Parser

`parse_env` handles the subset of dotenv syntax that appears in real repositories:

- `KEY=value`, `export KEY=value`;
- single and double quotes;
- `\n`, `\r`, `\t`, `\"`, `\\` escapes inside double quotes;
- inline comments after unquoted values;
- duplicate detection with line numbers.

It deliberately does **not** implement `${VAR}` interpolation or multiline values (the latter is tracked in `docs/roadmap.md`). A drift checker should compare the literal text a developer wrote, not the value after a runtime loader has transformed it.

When a quote is unterminated, the parser returns the literal content instead of raising: real `.env` files contain this often enough that a hard failure would be unhelpful. The trade-off is documented in the code.

## Schema

The schema is JSON, not TOML or YAML, for one reason: the standard library ships `json` on every supported Python version, while `tomllib` only arrived in Python 3.11. Zero runtime dependencies is a feature, not an accident.

A flat `{"PORT": "port"}` form is accepted because it makes small schemas pleasant to write by hand; the nested form is there for `required`, `pattern`, `choices`, `secret` and `description`.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | No errors (warnings may be present) |
| `1` | Validation errors, or `init` refused to overwrite a file |
| `2` | Missing file, unreadable schema, invalid JSON |

`--strict` promotes warnings to errors but does not change the exit-code contract: warnings become errors, so the result is still `1`.

This is intentionally boring: CI systems already understand `0`/non-zero.

## Secrets

The report never includes values, only key names and reasons. The `secret` flag and the name heuristic (`*_TOKEN`, `*_PASSWORD`, `*_API_KEY`, …) exist so future features (such as `--fix`) can treat those keys carefully.

A checker that prints a value to explain an error is a liability. `envscope` does not do it.

## Output stability

The JSON payload is a public interface:

```json
{"tool": "envscope", "version": "0.1.0", "ok": true, "summary": {}, "issues": []}
```

Adding fields is allowed; renaming or removing them is a breaking change. Tests assert the shape and the exit codes.

## Testing

Standard-library `unittest` only. The suite covers the parser, the schema loader, the checker and the CLI (via subprocess), because the CLI is the product. No mocks are needed: the tool has no network or filesystem side effects beyond reading two files and writing one.

## What would change at a larger scale

- A `--fix` mode needs atomic writes and a dry-run; see the roadmap.
- A pre-commit hook and a composite GitHub Action make adoption one line.
- Multiline values are the only parser feature likely to be requested by real users.

None of these require dependencies, a daemon, or a rewrite.
