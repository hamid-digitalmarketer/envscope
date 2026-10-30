# Publishing checklist

This repository is ready to publish as-is. The steps below are the only manual actions left.

## 1. Create the GitHub repository

Create a **public** repository named `envscope` on GitHub:

- owner: `NicolaRebecca`
- name: `envscope`
- description: `Audit .env files against .env.example and a JSON schema without printing secrets.`
- initialize with: **nothing** (no README, no .gitignore, no license)

## 2. Push the local repository

From the project root:

```bash
git remote add origin https://github.com/NicolaRebecca/envscope.git
git push -u origin main
git push --tags
```

If you use SSH:

```bash
git remote add origin git@github.com:NicolaRebecca/envscope.git
git push -u origin main
git push --tags
```

## 3. Verify CI

Open the **Actions** tab. The `CI` workflow runs the test suite on Python 3.9, 3.12 and 3.13. All jobs must be green.

## 4. Open the first three issues

Copy the titles and bodies from [`docs/roadmap.md`](docs/roadmap.md). Recommended labels:

| Issue | Label |
|---|---|
| Support multiline quoted values | `enhancement`, `good first issue` |
| Add `--fix` to append missing keys | `enhancement` |
| Ship a pre-commit hook and a reusable GitHub Action | `enhancement`, `help wanted` |

## 5. Use it in the Alignerr application

In the application, point to:

- repository: `https://github.com/NicolaRebecca/envscope`
- one line: *"A zero-dependency Python CLI that audits `.env` files against `.env.example` and a JSON schema, with secret masking and CI-friendly JSON output. 34 tests, GitHub Actions, MIT license."*

The project is personal: no employer code, no client data, no NDA material, no personal data. The examples use synthetic values only.

## 6. Optional: release

After the first merge:

```bash
git tag -a v0.1.1 -m "v0.1.1"
git push origin v0.1.1
```

Publishing to PyPI is not required for the Alignerr application. If you decide to publish later, add a `pypi` trusted-publisher workflow; do not upload secrets from this machine.
