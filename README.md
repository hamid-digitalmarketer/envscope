# envscope

**A zero-dependency CLI that audits `.env` files against `.env.example` and a JSON schema — and never prints secret values.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](#requirements)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

`envscope` catches the boring, expensive mistakes: a key added to `.env.example` but missing from production, a typo in `PORT`, a stale flag left in `.env`, a duplicate assignment that silently wins, a secret accidentally echoed to a CI log.

It is a small, readable project: standard library only, no network calls, no telemetry.

## Why

Environment drift is invisible until something breaks:

- a new variable works locally and is missing in staging;
- `DEBUG=true` is copied to production;
- `PORT=7000O` (letter O) passes code review but fails at boot;
- a CI script prints the whole `.env` to debug a problem.

`envscope` makes drift a build failure, not an incident.

## Features

- **Drift detection** — missing, extra and empty keys between `.env`, `.env.example` and the schema.
- **Type validation** — `string`, `int`, `float`, `bool`, `port`, `url`, `email`, plus `pattern` and `choices`.
- **Duplicate detection** — reports every line where a key is defined more than once.
- **Secret-aware** — values flagged `secret` (or matching names such as `*_TOKEN`, `*_PASSWORD`, `*_API_KEY`) are never printed.
- **CI-friendly** — `--json` output and stable exit codes.
- **Zero dependencies** — Python 3.9+, standard library only.
- **Fast** — parses and checks thousands of keys in milliseconds.

## Requirements

- Python 3.11 or newer
- macOS, Linux, or Windows

## Install

From a clone:

```bash
git clone https://github.com/NicolaRebecca/envscope.git
cd envscope
python -m pip install -e .
```

Or run it without installing:

```bash
PYTHONPATH=src python -m envscope --help
```

## Quick start

Generate a schema from your existing example file:

```bash
envscope init
# wrote envscope.json (10 variables)
```

Then check your local file:

```bash
envscope check
```

Example output on the deliberately broken demo in [`examples/`](examples/):

```text
envscope 0.1.0 | env=.env | example=.env.example | schema=envscope.json
-----------------------------------------------------------------------
ERROR             key DEBUG: must be true/false (or 1/0, yes/no, on/off) (line 4)
ERROR             key PORT: must be between 1 and 65535 (line 5)
WARN              missing key REDIS_URL
ERROR             key SMTP_FROM: must be a valid email address (line 8)
ERROR             key LOG_LEVEL: must be one of 'debug', 'info', 'warn', 'error' (line 9)
WARN              key EXTRA_FLAG is set in .env but not in .env.example or schema (line 11)
-----------------------------------------------------------------------
FAIL 9/10 keys present | 4 errors | 2 warnings
```

The exit code is `1`, so CI stops before deploying a broken configuration.

## Commands

### `envscope check`

| Flag | Default | Description |
|---|---|---|
| `--env` | `.env` | File to validate |
| `--example` | `.env.example` | Reference contract |
| `--schema` | `envscope.json` when present | JSON schema |
| `--strict` | off | Treat warnings (extra keys, optional missing) as errors |
| `--json` | off | Machine-readable report |
| `--quiet` | off | Print only the final summary |
| `--no-color` | off | Disable ANSI colours |

Exit codes: `0` success, `1` validation errors, `2` usage/file/schema error.

### `envscope init`

Builds a schema from `.env.example`, guessing types from names and values. Review the guesses; `init` is a starting point, not an oracle.

```bash
envscope init --example .env.example --out envscope.json
```

### `envscope version`

Prints the version.

## Schema format

`envscope.json`:

```json
{
  "variables": {
    "APP_ENV": {
      "type": "string",
      "choices": ["development", "staging", "production"]
    },
    "PORT": { "type": "port" },
    "DATABASE_URL": { "type": "url", "secret": true },
    "REDIS_URL": { "type": "url", "required": false },
    "LOG_LEVEL": {
      "type": "string",
      "choices": ["debug", "info", "warn", "error"]
    }
  }
}
```

A flat `{"PORT": "port"}` mapping is also accepted.

| Field | Type | Default | Notes |
|---|---|---|---|
| `type` | string | `string` | `string`, `int`, `float`, `bool`, `port`, `url`, `email` |
| `required` | bool | `true` | Missing required keys are errors |
| `pattern` | string | — | Full-match regular expression |
| `choices` | list | — | Allowed values |
| `secret` | bool | `false` | Masks values in future output |
| `description` | string | `""` | Human-readable note |

`url` accepts any absolute URL with a scheme and a host (`https://`, `postgres://`, `redis://`, …), not just HTTP.

## Use in CI

```yaml
- name: Validate environment contract
  run: |
    python -m pip install -e .
    envscope check --strict --json > envscope-report.json
  env:
    PYTHONPATH: src
```

The `--json` payload is stable and includes `ok`, `summary` and an `issues` array with `level`, `code`, `message`, `key` and `line`.

## Design principles

1. **Value-safe by default.** Secret-looking values are never printed; reports contain key names and reasons, not values.
2. **Boring on purpose.** No daemon, no network, no config discovery magic. A file in, a report out.
3. **Deterministic.** Same inputs → same output and exit code.
4. **Small surface.** One package, standard library, tests for every behaviour.

## Non-goals

- Variable interpolation (`${VAR}`) — use your runtime loader.
- Remote secret managers (Vault, AWS Secrets Manager).
- Rewriting `.env` files automatically (planned, see [`docs/roadmap.md`](docs/roadmap.md)).
- Replacing a real secrets scanner.

## Development

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

34 tests, no dependencies. The CI workflow runs the suite on Python 3.11, 3.12 and 3.13.

- Design decisions: [`docs/design.md`](docs/design.md)
- Captured example output: [`docs/demo.txt`](docs/demo.txt)

## Roadmap

See [`docs/roadmap.md`](docs/roadmap.md). The first three issues are intentionally small and self-contained.

## License

MIT — see [LICENSE](LICENSE).
