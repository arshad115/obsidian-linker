import json
import os
from typing import Dict, List, Optional, Set

STATE_VERSION = 1
STATE_FILENAME = 'vault-linker-state.json'
LEGACY_STATE_FILENAME = 'obsidian-linker-state.json'


def default_state_path(vault_root: str) -> str:
    return os.path.join(os.path.abspath(vault_root), '.obsidian', STATE_FILENAME)


def _legacy_state_path(vault_root: str) -> str:
    return os.path.join(os.path.abspath(vault_root), '.obsidian', LEGACY_STATE_FILENAME)


def _state_candidates(state_path: str) -> List[str]:
    candidates = [state_path]
    if state_path.endswith(STATE_FILENAME):
        legacy = state_path.replace(STATE_FILENAME, LEGACY_STATE_FILENAME)
        if legacy not in candidates:
            candidates.append(legacy)
    return candidates


def load_state(state_path: str) -> Dict:
    for path in _state_candidates(state_path):
        if not os.path.isfile(path):
            continue
        try:
            with open(path, 'r', encoding='utf-8') as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError):
            continue

        if data.get('version') != STATE_VERSION:
            return {'version': STATE_VERSION, 'paths': [], 'files': {}}
        return data

    return {'version': STATE_VERSION, 'paths': [], 'files': {}}


def save_state(state_path: str, markdown_files: List[str]) -> None:
    if state_path.endswith(LEGACY_STATE_FILENAME):
        state_path = state_path.replace(LEGACY_STATE_FILENAME, STATE_FILENAME)

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


def resolve_state_path(vault_root: str, explicit: Optional[str] = None) -> str:
    if explicit:
        return explicit
    return default_state_path(vault_root)
