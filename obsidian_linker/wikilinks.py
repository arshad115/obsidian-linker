import re
from typing import Dict, Tuple

from obsidian_linker.models import LinkPhrase

WIKILINK_PATTERN = re.compile(r'(?<!!)\[\[([^\]]+)\]\]')


def parse_wikilink_inner(inner: str) -> Tuple[str, str]:
    """Return (link target note name, visible text)."""
    if '|' in inner:
        left, display = inner.split('|', 1)
        target = left.split('#', 1)[0].strip()
        return target, display.strip()
    target = inner.split('#', 1)[0].strip()
    return target, target


def build_managed_link_keys(link_phrases: list) -> Dict[Tuple[str, str], LinkPhrase]:
    keys: Dict[Tuple[str, str], LinkPhrase] = {}
    for entry in link_phrases:
        keys[(entry.canonical.casefold(), entry.phrase.casefold())] = entry
    return keys
