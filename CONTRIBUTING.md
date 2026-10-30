# Contributing to envscope

Thanks for taking a look. This project is intentionally small: a bug report or a focused pull request is more useful than a large refactor.

## Development setup

```bash
git clone https://github.com/NicolaRebecca/envscope.git
cd envscope
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install -e .
```

## Run the tests

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

All tests must pass before a pull request is reviewed. There are no external test dependencies.

## Manual smoke test

```bash
cd examples
PYTHONPATH=../src python -m envscope check --example .env.example --env .env --schema envscope.json
```

The demo is supposed to fail: it contains four intentional errors and two warnings.

## Code style

- Standard library only for runtime code.
- Python 3.11+ only: use `from __future__ import annotations` for forward references; no support burden for older versions.
- Public functions get a short docstring explaining *why*, not a restatement of the name.
- No comments that describe obvious code.
- Keep output stable: tests and CI depend on exit codes and JSON shape.

## Commits and pull requests

- Use [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `test:`, `docs:`, `chore:`.
- One logical change per pull request.
- Add or update tests for behaviour changes.
- Describe the user-visible change and how you tested it.

## Reporting a bug

Open an issue with:

1. the version (`envscope version`);
2. the command you ran;
3. the relevant `.env.example` / schema (redact secrets);
4. expected vs actual output and exit code.

Do not paste real secrets. If you need to show a value, replace it with `***`.
