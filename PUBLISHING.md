# Publishing

## PyPI (`vaultlinker`)

The installable package name is **`vaultlinker`**. The console commands are **`vaultlinker`** and **`obsidian-linker`** (same CLI).

### One-time setup

1. Create an account on [pypi.org](https://pypi.org) if needed.
2. Do **not** use the taken name `obsidian-linker` on PyPI. This project publishes as **`vaultlinker`**.
3. Configure **trusted publishing**:
   - PyPI → **Publishing** → **Add a new pending publisher** (or add to project after first publish)
   - **PyPI project name:** `vaultlinker`
   - **Owner:** `arshad115`
   - **Repository name:** `obsidian-linker`
   - **Workflow name:** `release.yml`
   - **Environment name:** `pypi`
4. In GitHub: **Settings → Environments → New environment** named `pypi`.

### Release

```sh
git tag v0.4.0
git push origin v0.4.0
```

The [Release workflow](.github/workflows/release.yml) runs tests, publishes to PyPI, and uploads plugin assets to the GitHub Release.

```sh
pip install vaultlinker
vaultlinker --help
```

## Obsidian Community Plugins

The plugin is **not** listed in the community catalog until you submit it.

### Prerequisites

- A GitHub release for tag `v0.4.0` (or newer) with **`manifest.json`**, **`main.js`**, and **`versions.json`** attached.
- Plugin id **`obsidian-linker`** must be unique in the directory.

### Submit

1. Fork [obsidianmd/obsidian-releases](https://github.com/obsidianmd/obsidian-releases).
2. Edit `community-plugins.json` and add:

```json
{
  "id": "obsidian-linker",
  "name": "Obsidian Linker",
  "author": "Arshad Mehmood",
  "description": "Add, audit, and remove wikilinks when note titles and aliases appear in your vault.",
  "repo": "arshad115/obsidian-linker"
}
```

3. Open a pull request following [Obsidian’s plugin guidelines](https://docs.obsidian.md/Plugins/Releasing/Submit+your+plugin).

### Manual install

```sh
cd plugin && npm install && npm run build
```

Copy `main.js`, `manifest.json`, and `versions.json` into:

`YourVault/.obsidian/plugins/obsidian-linker/`
