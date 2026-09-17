# Vault Linker (plugin)

Desktop Obsidian plugin that adds `[[wikilinks]]` when note titles (and optional YAML aliases) appear in your vault.

## Install

1. Build the plugin:
   ```sh
   cd plugin
   npm install
   npm run build
   ```
2. Copy `main.js`, `manifest.json`, and `versions.json` from the **repo root** (build with `npm run build` in this folder) into:
   `VaultFolder/.obsidian/plugins/vault-linker/`
3. Enable **Vault Linker** under **Settings → Community plugins**.

## Commands

- **Link note titles in vault** / **Preview title links (dry run)**
- **Audit vault links** — pending links, broken wikilinks, zero-backlink notes
- **Remove managed title links** / **Preview removing managed links**

Settings align with the CLI: self-links, aliases, H1 headings, skip headings, min title length, ignored phrases.

![Vault Linker plugin settings](../images/plugin-settings.png)

CLI-only features: `--incremental`, `--jobs`, path globs, `--output` / `--backup`.

The [Python CLI](../README.md) (`pip install vaultlinker`) supports incremental runs, globs, and backups for larger workflows.
