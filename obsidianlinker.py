"""Backward-compatible facade for scripts that import obsidianlinker."""

from vault_linker import (
    LinkChange,
    LinkPhrase,
    LinkResult,
    find_markdown_files,
    link_files,
    resolve_exclude_dir_names,
)
from vault_linker.cli import main

__all__ = [
    "LinkChange",
    "LinkPhrase",
    "LinkResult",
    "find_markdown_files",
    "link_files",
    "main",
    "resolve_exclude_dir_names",
]

if __name__ == "__main__":
    main()
