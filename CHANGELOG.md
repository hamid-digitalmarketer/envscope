# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- Double-quoted dotenv values may span multiple lines; newlines are preserved and unterminated values are reported as parse errors.

## [0.1.0] - 2026-10-30

### Added

- `envscope check`: compare `.env` with `.env.example` and an optional JSON schema.
- Drift detection for missing, extra, empty and duplicate keys.
- Type validation for `string`, `int`, `float`, `bool`, `port`, `url`, `email`.
- `pattern` and `choices` constraints, with `required` and `secret` flags.
- `--strict`, `--json`, `--quiet` and `--no-color` options with stable exit codes.
- `envscope init`: generate a schema from `.env.example` by guessing types.
- `envscope version`.
- Unit and end-to-end tests (34 tests) using only the standard library.
- GitHub Actions CI on Python 3.11, 3.12 and 3.13.

[0.1.0]: https://github.com/NicolaRebecca/envscope/releases/tag/v0.1.0
