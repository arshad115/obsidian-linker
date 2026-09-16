# Obsidian Linker (plugin)

Desktop Obsidian plugin that adds `[[wikilinks]]` when note titles (and optional YAML aliases) appear in your vault.

## Install

1. Build the plugin:
   ```sh
   cd plugin
   npm install
   npm run build
   ```
2. Copy `main.js`, `manifest.json`, and `styles.css` (if present) into your vault:
   `VaultFolder/.obsidian/plugins/obsidian-linker/`
3. Enable **Obsidian Linker** under **Settings → Community plugins**.

## Commands

- **Link note titles in vault** — applies links across the vault.
- **Preview title links (dry run)** — counts links without writing files.

Settings mirror the CLI defaults (`no self links`, aliases, skip headings, ignored phrases).

The [Python CLI](../README.md) supports incremental runs, globs, and backups for larger workflows.
