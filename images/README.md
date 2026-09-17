# README images

| File | Purpose |
|------|---------|
| `before.png` / `after.png` | Graph-style before/after linking |
| `usage.png` | CLI dry run with `-v` and `--jobs` |
| `audit.png` | CLI `--audit` summary |
| `plugin-settings.png` | Obsidian plugin settings tab |

## Regenerate

From the repo root (requires `matplotlib`, `networkx`, `pillow`):

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]" matplotlib networkx pillow
PYTHONPATH=. python scripts/generate_readme_images.py
```

The script uses `images/fixtures/demo-vault/` for real CLI output in `usage.png` and redraws the graph PNGs. Replace `audit.png` manually or extend the script if you change audit output formatting.
