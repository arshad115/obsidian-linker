"""Backward-compatible facade for scripts and tests that import obsidianlinker."""

from obsidian_linker import (
    LinkChange,
    LinkPhrase,
    LinkResult,
    find_markdown_files,
    link_files,
    resolve_exclude_dir_names,
)
from obsidian_linker.cli import main

__all__ = [
    'LinkChange',
    'LinkPhrase',
    'LinkResult',
    'find_markdown_files',
    'link_files',
    'main',
    'resolve_exclude_dir_names',
]

if __name__ == '__main__':
    main()
