import fnmatch
import os
from typing import Iterable, List, Optional, Sequence, Set

from vault_linker.constants import DEFAULT_EXCLUDE_DIR_NAMES


def resolve_exclude_dir_names(
    use_default_excludes: bool,
    extra_excludes: Optional[Iterable[str]] = None,
) -> Set[str]:
    names: Set[str] = set()
    if use_default_excludes:
        names.update(DEFAULT_EXCLUDE_DIR_NAMES)
    if extra_excludes:
        names.update(extra_excludes)
    return names


def normalize_rel_path(path: str) -> str:
    return path.replace(os.sep, '/')


def path_matches_globs(
    rel_path: str,
    include_globs: Sequence[str],
    exclude_globs: Sequence[str],
) -> bool:
    rel_path = normalize_rel_path(rel_path)
    if exclude_globs and any(fnmatch.fnmatch(rel_path, pattern) for pattern in exclude_globs):
        return False
    if include_globs:
        return any(fnmatch.fnmatch(rel_path, pattern) for pattern in include_globs)
    return True


def find_markdown_files(
    directory: str,
    *,
    exclude_dir_names: Optional[Set[str]] = None,
    use_default_excludes: bool = True,
    extra_excludes: Optional[Iterable[str]] = None,
    include_globs: Optional[Sequence[str]] = None,
    exclude_globs: Optional[Sequence[str]] = None,
    verbose: bool = False,
) -> list:
    if exclude_dir_names is None:
        exclude_dir_names = resolve_exclude_dir_names(use_default_excludes, extra_excludes)

    include_globs = list(include_globs or [])
    exclude_globs = list(exclude_globs or [])
    directory = os.path.abspath(directory)

    markdown_files: List[str] = []
    if verbose:
        print(f"Searching for markdown files in directory: {directory}")

    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in exclude_dir_names]
        for file in files:
            if not file.endswith('.md'):
                continue
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, directory)
            if not path_matches_globs(rel_path, include_globs, exclude_globs):
                continue
            markdown_files.append(full_path)

    if verbose:
        print(f"Found {len(markdown_files)} markdown files.")
    return markdown_files
