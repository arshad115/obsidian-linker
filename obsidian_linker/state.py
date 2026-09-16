import json
import os
from typing import Dict, List, Optional, Set

STATE_VERSION = 1
DEFAULT_STATE_RELATIVE = os.path.join('.obsidian', 'obsidian-linker-state.json')


def default_state_path(vault_root: str) -> str:
    return os.path.join(os.path.abspath(vault_root), DEFAULT_STATE_RELATIVE)


def load_state(state_path: str) -> Dict:
    if not os.path.isfile(state_path):
        return {'version': STATE_VERSION, 'paths': [], 'files': {}}

    try:
        with open(state_path, 'r', encoding='utf-8') as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {'version': STATE_VERSION, 'paths': [], 'files': {}}

    if data.get('version') != STATE_VERSION:
        return {'version': STATE_VERSION, 'paths': [], 'files': {}}
    return data


def save_state(state_path: str, markdown_files: List[str]) -> None:
    files: Dict[str, float] = {}
    for path in markdown_files:
        try:
            files[os.path.abspath(path)] = os.path.getmtime(path)
        except OSError:
            continue

    payload = {
        'version': STATE_VERSION,
        'paths': sorted(files.keys()),
        'files': files,
    }
    os.makedirs(os.path.dirname(state_path), exist_ok=True)
    with open(state_path, 'w', encoding='utf-8') as handle:
        json.dump(payload, handle, indent=2)
        handle.write('\n')


def files_to_process(
    markdown_files: List[str],
    state: Dict,
    incremental: bool,
) -> Optional[Set[str]]:
    """Return None to process all files; otherwise the subset to process."""
    if not incremental:
        return None

    abs_paths = [os.path.abspath(path) for path in markdown_files]
    current_paths = set(abs_paths)
    previous_paths = set(state.get('paths', []))
    if current_paths != previous_paths:
        return None

    previous_mtimes = state.get('files', {})
    changed = set()
    for path in abs_paths:
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            changed.add(path)
            continue
        if previous_mtimes.get(path) != mtime:
            changed.add(path)
    return changed
