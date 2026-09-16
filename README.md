# Obsidian Linker

[![Run Tests](https://github.com/arshad115/obsidian-linker/actions/workflows/run-tests.yml/badge.svg)](https://github.com/arshad115/obsidian-linker/actions/workflows/run-tests.yml)

## Overview

Obsidian Linker is a tool designed to help you manage and link your notes in Obsidian. It provides various features to enhance your note-taking experience.

## Linking

<p float="left">
  <img src="images/before.png" alt="Before" width="45%" />
  <img src="images/after.png" alt="After" width="45%" />
</p>

## Features

- Automatic linking of notes
- Uses Wikilink format
- Skip links in metadata
- Skip links in codeblocks, inline code

## Linking Process

1. **Scan Files**: The tool scans all the markdown files in your Obsidian vault.
2. **Extract Filenames**: It extracts the filenames from the scanned files.
3. **Match Filenames**: It matches the filenames with the content in other files, ignoring the case.
4. **Insert Links**: When a match is found, it inserts a Wikilink in the content, preserving the original case of the filename in the link.
5. **Skip Metadata and Code**: The tool skips adding links in metadata sections and code blocks to avoid unwanted linking.

### Examples

- **Simple Linking**: If a file named `Object-Oriented Programming.md` exists and another file mentions "object-oriented programming", the tool will link it as `[[object-oriented programming]]`.
- **Preserve Case**: If the mention is "Object-Oriented Programming", the link will be `[[Object-Oriented Programming]]`.
- **No Links in Code Blocks**: Mentions inside code blocks are ignored.
- **No Links in Metadata**: Mentions inside metadata sections are ignored.
- **Multiple Links**: If multiple files are mentioned, each will be linked appropriately.
- **Partial Matches**: If a file named `Object.md` exists, mentions of "object" will be linked as `[[object]]`, but "objects" will not be linked.
- **Complex Linking**: If files named `Object-Oriented Programming.md`, `Functional Programming.md`, and `Object.md` exist, and another file mentions "object-oriented programming", "functional programming", and "object", each will be linked as `[[object-oriented programming]]`, `[[functional programming]]`, and `[[object]]` respectively. Note "object" will not be added inside "object-oriented programming".

## Installation

### From PyPI

```sh
pip install vaultlinker
vaultlinker /path/to/vault/ --help
# or: obsidian-linker /path/to/vault/ --help
```

### From source

Clone the repository and install the package (recommended):

```sh
git clone https://github.com/arshad115/obsidian-linker.git
cd obsidian-linker
pip install -e ".[dev]"
```

For a quick script-only install without the console command:

```sh
pip install -r requirements.txt
```

## Usage

![Usage Image](images/usage.png)

After installation:

```sh
obsidian-linker /path/to/vault/
```

Or run the module directly:

```sh
python obsidianlinker.py /path/to/vault/
```

Use `-v` / `--verbose` for progress bars and scan details (default is quiet except warnings and the summary).

Parallel processing (read, link, and write phases):

```sh
obsidian-linker /path/to/vault/ --jobs 8
obsidian-linker /path/to/vault/ --jobs 0   # automatic worker count
```

### Safety options

Preview changes without writing files:

```sh
python obsidianlinker.py /path/to/vault/ --dry-run
```

Write linked copies to another directory (vault files stay unchanged):

```sh
python obsidianlinker.py /path/to/vault/ --output /path/to/linked-vault/
```

Create a `.bak` copy of each file before overwriting it in the vault:

```sh
python obsidianlinker.py /path/to/vault/ --backup
```

Skip linking a note's title inside its own file (e.g. do not turn `README` into `[[README]]` in `README.md`):

```sh
python obsidianlinker.py /path/to/vault/ --no-self-links
```

By default, markdown under `.obsidian`, `.git`, `attachments`, and similar folders is skipped. Add more directory names with `--exclude DIRNAME`, or pass `--no-default-excludes` to scan everything.

Limit which notes are processed with vault-relative globs:

```sh
obsidian-linker /path/to/vault/ --include-glob 'notes/**' --exclude-glob 'templates/**'
```

### Obsidian-aware linking

- **Aliases**: YAML `alias` / `aliases` in front matter are link phrases; matches use `[[Note Title|alias]]` when the visible text differs from the note title.
- **Embeds & markdown links**: Text inside `![[...]]` and `[label](url)` is not linked.
- **Headings**: Text on `# heading` lines is skipped unless you pass `--link-headings`.
- **Duplicate filenames**: If two notes share the same filename in different folders, the tool warns and uses the note with the longest path as the link target for that title.
- **`--use-headings`**: Also link phrases taken from each note's first `# H1` heading.
- **`--no-aliases`**: Only use filenames, not front matter aliases.

### Audit and unlink

Audit the vault (no file changes):

```sh
obsidian-linker /path/to/vault/ --audit
obsidian-linker /path/to/vault/ --audit -v   # include pending link details
```

Reports pending links (same rules as a dry run), broken `[[wikilinks]]` with no matching note, notes with zero incoming links, and the most-linked titles.

Remove wikilinks that this tool would create (title and alias forms only; manual links to other targets are kept):

```sh
obsidian-linker /path/to/vault/ --unlink --dry-run
obsidian-linker /path/to/vault/ --unlink --backup
```

### Incremental and blocklist

Re-run only notes that changed since the last successful incremental run (state is stored in `.obsidian/obsidian-linker-state.json`). If notes are added or removed, every note is processed again so new titles can link correctly.

```sh
obsidian-linker /path/to/vault/ --incremental
```

Skip noisy short titles or specific words:

```sh
obsidian-linker /path/to/vault/ --ignore-phrase README --min-title-length 4
obsidian-linker /path/to/vault/ --ignore-file ./linker-ignore.txt
```

## Obsidian plugin

A community plugin lives in [`plugin/`](plugin/) (source); `manifest.json`, `versions.json`, and `main.js` are at the **repo root** for Obsidian’s directory scanner. Build with `cd plugin && npm install && npm run build`, then submit via [community.obsidian.md](https://community.obsidian.md). See [plugin/README.md](plugin/README.md) and [PUBLISHING.md](PUBLISHING.md).

Make sure to back up your vault before using this tool, as in-place runs can make irreversible edits unless you use `--dry-run` or `--output`.
## Running Tests

To run tests for Obsidian Linker, use the following command:
```sh
pytest
```

This will execute all the tests and provide you with a summary of the results. Make sure you have all the necessary dependencies installed before running the tests.

## TODO

- [x] Add support for alias links
- [x] Multithreading
- [ ] Write additional tests for edge cases
- [x] Make it into a plugin for Obsidian

## Contributors

- [Arshad Mehmood](https://github.com/arshad115)

## Contributing

We welcome contributions to Obsidian Linker! If you have an idea for a new feature or have found a bug, please open an issue or submit a pull request.

### Steps to Contribute

1. Fork the repository.
2. Create a new branch for your feature or bugfix:
    ```sh
    git checkout -b feature-name
    ```
3. Make your changes and commit them:
    ```sh
    git commit -m "Description of your changes"
    ```
4. Push your changes to your fork:
    ```sh
    git push origin feature-name
    ```
5. Open a pull request on the main repository.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details. © Arshad Mehmood


