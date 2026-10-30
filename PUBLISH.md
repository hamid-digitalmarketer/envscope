# Publishing checklist

**Status: published.**

- Repository: <https://github.com/NicolaRebecca/envscope>
- Default branch: `main`
- Release: `v0.1.0`
- CI: green on Python 3.11, 3.12 and 3.13
- Issues: #1 multiline values, #2 `--fix`, #3 pre-commit hook / GitHub Action

The project is personal: no employer code, no client data, no NDA material, no personal data. The examples use synthetic values only.

## Next releases

```bash
# after a change is merged
git tag -a v0.1.1 -m "v0.1.1"
git push origin main --tags
```

Publishing to PyPI is not required for the Alignerr application. If you decide to publish later, add a `pypi` trusted-publisher workflow; do not upload secrets from this machine.

## If the repository has to be recreated

1. Create a public repository named `envscope` (no README, no .gitignore, no license).
2. Add the remote and push:
   ```bash
   git remote add origin https://github.com/NicolaRebecca/envscope.git
   git push -u origin main
   git push --tags
   ```
3. Verify the `CI` workflow is green and re-create issues #1–#3 from [`docs/roadmap.md`](docs/roadmap.md).
