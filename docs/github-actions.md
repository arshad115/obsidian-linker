# GitHub Actions

This repo includes [`.github/workflows/vault-linker-example.yml`](../.github/workflows/vault-linker-example.yml), which audits and dry-runs linking on `images/fixtures/demo-vault/`.

## Use on your own vault

1. Check out your vault (private repo or submodule) in the workflow.
2. Install Vault Linker:

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: "3.12"
- run: pip install vaultlinker
```

3. Run without modifying files first:

```yaml
- run: vaultlinker "${{ github.workspace }}/vault" --audit -v
- run: vaultlinker "${{ github.workspace }}/vault" --dry-run -v --jobs 8
```

4. Optionally link on a schedule (use `--backup`):

```yaml
- run: vaultlinker "${{ github.workspace }}/vault" --backup --jobs 8
```

Limit scope with globs:

```yaml
- run: vaultlinker ./vault --include-glob 'notes/**' --exclude-glob 'templates/**' --dry-run
```
